from django.shortcuts import render, redirect
import re
from django_redis import get_redis_connection
from redis import StrictRedis
from .models import User, Address
from django.urls import reverse
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import SignatureExpired
from django.http import HttpResponse
from django.core.mail import send_mail
from django.contrib.auth import authenticate, user_logged_in, user_logged_out, login, logout
# from celery_tasks.tasks import send_reister_active_email
from django.contrib.auth.decorators import login_required
from utils.mixin import LoginRequiredMixin
from django.template import RequestContext
from ..goods.models import GoodsSKU
from ..order.models import OrderInfo, OrderGoods
from django.core.paginator import Paginator

"""
# Create your views here.
# def register(request):
#     if request.method == 'GET':
#         return render(request,'register.html')
#     else:
#         # 进行注册处理
#         # 接收数据
#         username = request.POST.get('user_name')
#         password = request.POST.get('pwd')
#         email = request.POST.get('email')
#         allow = request.POST.get('allow')
#
#         # 进行数据校验
#         if not all([username, password, email]):
#             return render(request, 'register.html', {'errmsg': '数据不完整'})
#
#         # 校验邮箱
#         if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
#             return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})
#
#         # 是否同意用户协议
#         if allow != 'on':
#             return render(request, 'register.html', {'errmsg': '请同意用户协议'})
#         # 校验用户名是否重复
#         try:
#             user = User.objects.get(username=username)
#         except User.DoesNotExist:
#             # 用户名不存在
#             user = None
#         if user:
#             # 用户名已存在
#             return render(request, 'register.html', {'errmsg': '用户名已存在'})
#
#         # 进行业务处理:进行用户注册
#         # user = User()
#         # user.username = username
#         # user.password = password
#         # user.email = email
#         # user.save()
#         user = User.objects.create_user(username, password, email)
#         user.is_active = 0
#         user.save()
#
#         # 返回应答
#         return redirect(reverse('goods:index'))


# def register_handle(request):
#     #进行注册处理
#     #接收数据
#     username = request.POST.get('user_name')
#     password = request.POST.get('pwd')
#     email = request.POST.get('email')
#     allow = request.POST.get('allow')
#
#     #进行数据校验
#     if not all([username,password,email]):
#         return render(request,'register.html',{'errmsg':'数据不完整'})
#
#     #校验邮箱
#     if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
#         return render(request,'register.html',{'errmsg':'邮箱格式不正确'})
#
#     #是否同意用户协议
#     if allow != 'on':
#         return render(request,'register.html',{'errmsg':'请同意用户协议'})
#     #校验用户名是否重复
#     try:
#         user = User.objects.get(username=username)
#     except User.DoesNotExist:
#         #用户名不存在
#         user =None
#     if user:
#         #用户名已存在
#         return render(request,'register.html',{'errmsg':'用户名已存在'})
#
#     #进行业务处理:进行用户注册
#     # user = User()
#     # user.username = username
#     # user.password = password
#     # user.email = email
#     # user.save()
#     user = User.objects.create_user(username,password,email)
#     user.is_active = 0
#     user.save()
#
#
#     #返回应答
#     return redirect(reverse('goods:index'))
"""

class RegisterView(View):
    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('user_name')
        password = request.POST.get('pwd')
        email = request.POST.get('email')
        allow = request.POST.get('allow')

        # 进行数据校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})

        # 校验邮箱
        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        # 是否同意用户协议
        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意用户协议'})
        # 校验用户名是否重复
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # 用户名不存在
            user = None
        if user:
            # 用户名已存在
            return render(request, 'register.html', {'errmsg': '用户名已存在'})

        # 进行业务处理:进行用户注册
        # user = User()
        # user.username = username
        # user.password = password
        # user.email = email
        # user.save()
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()
        serializer = Serializer(settings.SECRET_KEY, 3600)
        info = {'confirm': user.id}
        token = serializer.dumps(info)  # bytes
        token = token.decode()
        # 发邮件
        subject = '天天生鲜欢迎'  # 主题
        message = ''  # 正文
        sender = settings.EMAIL_FROM  # 发件人
        receiver = [email]  # 收件人列表
        html_message = '<h1>%s,欢迎使用守望先锋</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s<a/>' % (
            username, token, token)
        send_mail(subject, message, sender, receiver, html_message=html_message)
        # send_reister_active_email.delay(username,email,token)    #使用celery处理请求
        # 返回应答
        return redirect(reverse('goods:index'))


class ActiveView(View):
    # 用户激活
    def get(self, request, token):
        serializer = Serializer(settings.SECRET_KEY, 3600)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 跳转到登录页面
            return redirect(reverse('user:login'))

        except SignatureExpired:
            # 激活连接已过期
            return HttpResponse('激活连接已过期')





class LoginView(View):
    def get(self, request):
        """显示登录页面"""
        # 判断是否记住用户名

        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'login.html', {'username': username, 'checked': checked})

        # return render(request,'login.html')

    def post(self, request):
        """登录校验"""

        # 接收数据
        username = request.POST.get('username')
        password = request.POST.get('pwd')

        # 校验数据
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})

        # 业务处理
        user = authenticate(username=username, password=password)  # authenicated无法使用，存在bug
        # 查资料发现只要在setting文件里面加上AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.AllowAllUsersModelBackend']让他不自动关联数据库的is_active即可完美解决。

        if user is not None:
            if user.is_active:
                # 记录登陆状态 session
                # login(request, user)
                login(request, user)
                # 获取登陆后要跳转的地址, 默认跳转首页 ,运行后发先无法获取
                # next_url = request.GET.get('next', reverse('goods:index'))
                # response = redirect(next_url)  # HttpResponseRedirect
                response = redirect(reverse('goods:index'))
                # 判断是否记住用户名
                remember = request.POST.get('remember')
                if remember == 'on':
                    response.set_cookie('username', username, max_age=24 * 3600)
                else:
                    response.delete_cookie(username)
                # return redirect(reverse('goods:index'))
                return response
            else:
                return render(request, 'login.html', {'errmsg': '账户未激活'})

        else:
            return render(request, 'login.html', {'errmsg': '用户名或密码错误'})


class LogoutView(View):
    def get(self, request):
        """退出登录"""
        # user_logged_out(request)
        logout(request)
        return redirect(reverse('user:login'))


class UserInfoView(LoginRequiredMixin, View):  #

    def get(self, request):
        """用户信息页"""
        # page = 'user
        # 获取用户信息
        user = request.user
        address = Address.objects.get_default_address(user)
        sr = StrictRedis(host='127.0.0.1', port='6379', db=1)
        con = get_redis_connection('default')

        history_key = 'history_%d' % user.id
        sku_ids = con.lrange(history_key, 0, 4)
        # sku_ids = GoodsSKU.objects.filter(id_in=sku_ids)

        goods_li = []
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=1)
            goods_li.append(goods)

        context = {
            'page': 'user',
            'address': address,
            'goods_li': goods_li

        }

        # 获取用户的历史浏览记录
        return render(request, 'user_center_info.html', context)


class UserOrderView(LoginRequiredMixin, View):  # LoginRequiredMixin,

    def get(self, request, page):
        """用户订单页"""
        # page ='order
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        # 遍历获取订单商品的信息
        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 遍历order_skus计算商品小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku属性amount,保存订单商品小计
                order_sku.amount = amount

            # 动态给order属性，保存订单状态标题
            order.staus_name = OrderInfo.ORDER_STATUS[order.order_status]

            # 动态给order属性，保存订单商品信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的page实例对象
        skus_page = paginator.page(page)

        # 1.总页数小于5页 显示全部页面
        # 2.如果当前页面是前三页，显示前五页的页码
        # 3.如果当前页是后三页，显示后五页
        # 4.其他情况，显示当前页的前两页和当前页的后两页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages)
        else:
            pages = range(page - 2, page + 3)

        # 组织上下文
        context = {
            'skus_page': skus_page,
            'pages': pages,
            'page': 'order'
        }

        return render(request, 'user_center_order.html', context)


class AddressView(LoginRequiredMixin, View):  # LoginRequiredMixin,
    # @login_required
    def get(self, request):
        # 用户地址页
        # page = 'address
        # 获取用户的默认收货地址
        user = request.user
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'address', 'address': address})

    def post(self, request):
        # 接收数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code ')
        phone = request.POST.get('phone')

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user_center_site.html', {'errmsg': '手机格式不正确'})

        # 业务处理 地址添加
        # 如果用户已存在默认收货地址，添加的地址不作为默认地址，否则作为默认收货地址

        user = request.user
        print(user)
        # try:
        #     address = Address.objects.get(user=user,is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True
        # 添加地址
        Address.objects.create(user=user, receiver=receiver, addr=addr, zip_code=zip_code, phone=phone,
                               is_default=is_default)

        # 返回应答
        return redirect(reverse('user:address'))
