from django.shortcuts import render, redirect
from django.template import RequestContext
from django.views.generic import View
from .models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner, GoodsSKU
from django_redis import get_redis_connection
from django.core.cache import cache
from django.urls import reverse
from ..order.models import OrderGoods
from django.core.paginator import Paginator


# Create your views here.
class IndexView(View):

    def get(self, request):
        # 尝试从缓存中获取数据
        context = cache.get('index_page_data')

        if context is None:

            # 获取商品种类信息
            types = GoodsType.objects.all()

            # 获取首页轮播商品信息
            goods_banners = IndexGoodsBanner.objects.all().order_by('index')

            # 获取首页促销活动信息
            promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

            # 获取首页分类商品展示信息
            # type_goods = IndexTypeGoodsBanner.objects.all()
            for type in types:
                image_banners = IndexTypeGoodsBanner.objects.filter(type=type, display_type=1).order_by('index')
                tittle_banner = IndexTypeGoodsBanner.objects.filter(type=type, display_type=0).order_by('index')
                type.image_banners = image_banners
                type.title_banners = tittle_banner

            # 设置缓存
            context = {
                'types': types,
                'goods_banners': goods_banners,
                'promotion_banners': promotion_banners
            }
            cache.set('index_page_data', context, 3600)

            # 获取用户购物车中商品的数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        context.update(cart_count=cart_count)

        return render(request, 'index.html', context)


class DetailView(View):
    """详情页"""

    def get(self, request, goods_id):
        """显示详情页"""
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except GoodsSKU.DoesNotExist:
            return redirect(reverse('goods:index'))
        # sku = GoodsSKU.objects.get(id=goods_id)
        # 获取商品的分类信息
        types = GoodsType.objects.all()
        sku_order = OrderGoods.objects.filter(sku=sku).exclude(comment='')
        # 获取新品信息
        new_sku = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')  # 降序

        # 获取同一个spu的其他规格商品
        same_spu_skus = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车中的商品数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 移除列表中的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 吧goods_id插入到列表左侧
            conn.lpush(history_key, goods_id)
            # 只保存用户最新浏览的五条信息
            conn.ltrim(history_key, 0, 4)

        # 组织模板上下文
        context = {'sku': sku,
                   'types': types,
                   'new_sku': new_sku,
                   'sku_order': sku_order,
                   'cart_count': cart_count,
                   'same_spu_skus': same_spu_skus
                   }

        return render(request, 'detail.html', context)


class ListView(View):
    """列表页"""

    # 种类id 页码 排序方式
    # /list/种类id/页码/排序方式
    def get(self, request, type_id, page):
        try:
            type = GoodsType.objects.get(id=type_id)
        except GoodsType.DoesNotExist:
            return redirect(reverse('goods:index'))
        # 获取分类商品信息
        types = GoodsSKU.objects.filter(type=type)
        # 获取排序方式
        # sort = default 按照默认id排序
        # sort = price 按照价格排序
        # sort = hot 按照商品销量排序
        # 获取商品的分类信息
        sort = request.GET.get('sort')
        # 降序 从高到底
        if sort == 'price':
            skus = GoodsType.objects.filter(type=type).order_by('price')  # 升序 从低祷告
        elif sort == 'hot':
            skus = GoodsType.objects.filter(type=type).order_by('-hot')  # 降序 从高到低
        else:
            skus = GoodsType.objects.filter(type=type).order_by('-id')

        # 对数据进行分页
        paginator = Paginator(skus, 1)

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

        # 获取新品信息
        new_sku = GoodsSKU.objects.filter(type=type).order_by('-create_time')

        # 获取用户购物车中的商品数目
        user = request.user
        cart_count = 0
        if user.is_authenticated:
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            cart_count = conn.hlen(cart_key)

        # 组织模板上下文
        context = {
            'type': type,
            'types': types,
            'skus_page': skus_page,
            'cart_count': cart_count,
            'pages': pages,
            'sort': sort
        }

        return render(request, 'list.html', context)
