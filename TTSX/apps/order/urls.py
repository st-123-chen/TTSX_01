from django.conf.urls import url
from ..order.views import PlaceOrderView, OrderCommitView, OrderPayView, OrderCheckView, CommentView
from django.urls import path, re_path

urlpatterns = [
    path('place', PlaceOrderView.as_view(), name='place'),
    path('commit', OrderCommitView.as_view(), name='commit'),
    path('pay', OrderPayView.as_view(), name='pay'),
    path('check', OrderCheckView.as_view(), name='check'),
    re_path('comment/(?P<order_id>.+)', CommentView.as_view(), name='commit')
]
