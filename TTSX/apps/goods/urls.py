from django.conf.urls import url
from django.urls import path, re_path
from .views import IndexView, DetailView, ListView

urlpatterns = [
    # path('index',IndexView.as_view(),name='index'),
    # re_path('goods/(?P<goods_id>\d+)$',DetailView.as_view(),name='detail'),
    # re_path('list/(?P<type_id>\d+)/(?P<page>\d+)$',List_View.as_view(),name='list')

    path('index/', IndexView.as_view(), name='index'),  # 首页
    path('goods/<int:goods_id>', DetailView.as_view(), name='detail'),  # 详情页
    path('list/<int:type_id>/<int:page>', ListView.as_view(), name='list    '),  # 详情页

]
