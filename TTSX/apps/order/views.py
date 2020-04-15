from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import View
from django_redis import get_redis_connection
from ..goods.models import GoodsSKU
from ..user.models import Address
from utils.mixin import LoginRequiredMixin
from django.http import JsonResponse
from ..order.models import OrderInfo, OrderGoods
from datetime import datetime
from django.db import transaction
from alipay import AliPay
import os
from TTSX import settings


# Create your views here.

class PlaceOrderView(LoginRequiredMixin, View):

    def post(self, request):
        user = request.user
        # 获取参数sku_ids
        sku_ids = request.POST.getlist('sku_ids')

        # 验证参数完整性
        if not sku_ids:
            return redirect(reverse('cart:add'))

        # 获取用户购物车中的商品信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 尝试获取sku_id的值
        # 保存模式为字典{'sku_id':sku_id,'count':count}

        sku_dict = []
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            amount = sku.price * int(count)

            sku.amount = amount
            sku.count = count
            sku_dict.append(sku)
            total_count += int(count)
            total_price += amount

        # 获取用户运费
        transit_price = 0

        # 获取用户地址
        addr = Address.objects.get(user=user)

        # 计算实际总价格
        total_pay = total_price + transit_price

        # 组织模板上下文

        context = {
            'sku_dict': sku_dict,
            'total_count': total_count,
            'total_price': total_price,
            'transit_price': transit_price,
            'total_pay': total_pay,
            'addr': addr
        }

        # 返回应答
        return render(request, 'place_order.html', context)

        # return render(request, 'place_order.html')


# 前端传递的参数：地址id(addr_id ) 支付方式（pay_method) 用户要购买的商品id字符串（sku_ids）
# 悲观锁
class OrderCommitView(View):
    # 使用mysql数据库的事务性
    @transaction.atomic
    def post(self, request):
        # 用户登录验证，由于是ajax后台请求 无法使用LoginRequiredMixin
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验数据完整性
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '数据非法'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)

        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '数据不存在'})

        #
        # 业务处理
        # todo:创建订单
        # 组织参数
        # 订单id:时间+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        # 运费
        transit_price = 0

        # 总数目和总金额
        total_price = 0
        total_count = 0

        # 设置一个mysql数据库的事务保存点
        save_id = transaction.savepoint()

        try:
            # 向df_order_info中添加记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # 用户的订单中存在几个商品，就需要向数据表中添加几条记录
            # 获取用户购物车中的商品信息
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                # 获取商品信息
                try:
                    # sku = GoodsSKU.objects.get(id=sku_id) 普通查询
                    sku = GoodsSKU.objects.select_for_update().get(
                        id=sku_id)  # 添加悲观锁(select * from xx where id=xx for update)
                except:
                    # 商品不存在
                    # 进行事务回滚
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                # 从redis中获取用户所需要购买的商品的数量
                count = conn.hget(cart_key, sku_id)

                # todo：判断商品库存
                if int(count) > sku.stock:
                    transaction.savepoint_rollback(save_id)  # 进行事务回滚
                    return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                # 向数据表中添加记录
                OrderGoods.objects.create(order=order,
                                          sku=sku,
                                          count=count,
                                          price=sku.price)

                # todo：更新商品的库存和销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()

                # todo：累加计算订单商品的总数量和总价格
                amount = sku.price * int(count)
                total_count += int(count)
                total_price += amount

            # todo:更新订单信息表中的商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as f:  # 如果存在异常 则进行回滚
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # todo：清除用户购物车中的数据
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'errmsg': '订单提交成功'})


# 乐观锁
class OrderCommitView1(View):
    # 使用mysql数据库的事务性
    @transaction.atomic
    def post(self, request):
        # 用户登录验证，由于是ajax后台请求 无法使用LoginRequiredMixin
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')

        # 校验数据完整性
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        # 校验支付方式
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '数据非法'})

        # 校验地址
        try:
            addr = Address.objects.get(id=addr_id)

        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '数据不存在'})

        #
        # 业务处理
        # todo:创建订单
        # 组织参数
        # 订单id:时间+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

        # 运费
        transit_price = 0

        # 总数目和总金额
        total_price = 0
        total_count = 0

        # 设置一个mysql数据库的事务保存点
        save_id = transaction.savepoint()

        try:
            # 向df_order_info中添加记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # 用户的订单中存在几个商品，就需要向数据表中添加几条记录
            # 获取用户购物车中的商品信息
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    # 获取商品信息
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)  # 普通查询
                        # sku = GoodsSKU.objects.select_for_update().get(
                        #     id=sku_id)   添加悲观锁(select * from xx where id=xx for update)
                    except:
                        # 商品不存在
                        # 进行事务回滚
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品不存在'})

                    # 从redis中获取用户所需要购买的商品的数量
                    count = conn.hget(cart_key, sku_id)

                    # todo：判断商品库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)  # 进行事务回滚
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # todo：更新商品的库存和销量
                    # sku.stock -= int(count)
                    # sku.sales += int(count)
                    # sku.save()
                    orgin_stack = sku.stock
                    new_stock = orgin_stack - int(count)
                    new_sales = sku.sales + int(count)

                    # 更新商品库存为new_stock 更新商品销售额为new_sales
                    # 判断剩余库存是否为查询出的库存
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stack).update(stock=new_stock,
                                                                                       sales=new_sales)  # 返回受影响的行数
                    if res == 0:
                        if i == 2:
                            # 库存被改动
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 7, 'errmsg': '下单失败'})
                        continue

                    # 向数据表中添加记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # todo：累加计算订单商品的总数量和总价格
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount

                    # 跳出循环
                    break

            # todo:更新订单信息表中的商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as f:  # 如果存在异常 则进行回滚
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交事务
        transaction.savepoint_commit(save_id)

        # todo：清除用户购物车中的数据
        conn.hdel(cart_key, *sku_ids)  # 拆包

        # 返回应答
        return JsonResponse({'res': 5, 'errmsg': '订单提交成功'})


# 订单支付
class OrderPayView(View):
    """订单支付"""

    def post(self, request):
        """订单支付"""

        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 0, 'errmsg': '订单编号不存在'})

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)

        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '订单错误'})

        # 业务处理：使用python 调用支付宝的支付接口

        alipay = AliPay(
            appid="2016102300747619",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=os.path.join(settings.BASE_DIR, 'alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do? + order_string
        total_pay = order.total_price + order.transit_price  # Decimal类型
        order_string = alipay.api_alipay_trade_page_pay(
            out_trade_no=order_id,
            total_amount=str(total_pay),  # 支付总金额
            subject='天天生鲜%s' % order_id,
            return_url=None,
            notify_url=None  # 可选, 不填则使用默认notify url
        )
        # 返回应答
        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


# ajax请求 post
# 前端传递的参数order_id

class OrderCheckView(View):
    """查看订单支付结果"""

    def post(self, request):
        """查询支付结果"""
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

        # 接收参数
        order_id = request.POST.get('order_id')

        # 校验参数
        if not order_id:
            return JsonResponse({'res': 0, 'errmsg': '订单编号不存在'})

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user, pay_method=3, order_status=1)

        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 1, 'errmsg': '订单错误'})

        # 业务处理：使用python 调用支付宝的支付接口

        alipay = AliPay(
            appid="2016102300747619",
            app_notify_url=None,  # 默认回调url
            app_private_key_string=os.path.join(settings.BASE_DIR, 'apps/order/app_private_key.pem'),
            # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
            alipay_public_key_string=os.path.join(settings.BASE_DIR, 'alipay_public_key.pem'),
            sign_type="RSA2",  # RSA 或者 RSA2
            debug=True  # 默认False
        )

        # 调用支付宝的查询接口
        while True:
            response = alipay.api_alipay_trade_query(order_id)
            """
            
            response = {
    
                    "trade_no": "2017032121001004070200176844",
                    "code": "10000",
                    "invoice_amount": "20.00",
                    "open_id": "20880072506750308812798160715407",
                    "fund_bill_list": [
                        {
                            "amount": "20.00",
                            "fund_channel": "ALIPAYACCOUNT"
                        }
                    ],
                    "buyer_logon_id": "csq***@sandbox.com",
                    "send_pay_date": "2017-03-21 13:29:17",
                    "receipt_amount": "20.00",
                    "out_trade_no": "out_trade_no15",
                    "buyer_pay_amount": "20.00",
                    "buyer_user_id": "2088102169481075",
                    "msg": "Success",
                    "point_amount": "0.00",
                    "trade_status": "TRADE_SUCCESS",
                    "total_amount": "20.00"
                }
                
            """

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 支付成功
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                # 更新订单状态
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                # 返回结果
                return JsonResponse({'res': 3, 'message': '支付成功'})

            elif code == '4004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款 or 业务处理失败 可能稍后会处理成功
                import time
                time.sleep(5)
                continue

            else:
                # 支付出错
                # 返回错误信息
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})


class CommentView(LoginRequiredMixin, View):
    """订单评论"""

    def get(self, request, order_id):
        """提供评论页面"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 根据订单的状态获取订单的状态标题
        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        # 获取订单商品信息
        order_skus = OrderGoods.objects.filter(order_id=order_id)
        for order_sku in order_skus:
            # 计算商品的小计
            amount = order_sku.count * order_sku.price
            # 动态给order_sku增加属性amount,保存商品小计
            order_sku.amount = amount
        # 动态给order增加属性order_skus, 保存订单商品信息
        order.order_skus = order_skus

        # 使用模板
        return render(request, "order_comment.html", {"order": order})

    def post(self, request, order_id):
        """处理评论内容"""
        user = request.user
        # 校验数据
        if not order_id:
            return redirect(reverse('user:order'))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse("user:order"))

        # 获取评论条数
        total_count = request.POST.get("total_count")
        total_count = int(total_count)

        # 循环获取订单中商品的评论内容
        for i in range(1, total_count + 1):
            # 获取评论的商品的id
            sku_id = request.POST.get("sku_%d" % i)
            # 获取评论的商品的内容
            content = request.POST.get('content_%d' % i, '')
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue

            order_goods.comment = content
            order_goods.save()

        order.order_status = 5  # 已完成
        order.save()

        return redirect(reverse("user:order", kwargs={"page": 1}))
