from django.urls import path, re_path
from django.contrib.auth.decorators import login_required

from .views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView

urlpatterns = [
    # path('register',views.register,name='register'),
    # path('register_handle',views.register_handle,name='register_handle'),
    # path('user',login_required(UserInfoView.as_view()),name='user'),
    # path('order',login_required(UserOrderView.as_view()),name='order'),
    # path('address',login_required(AddressView.as_view()),name='address')

    path('register', RegisterView.as_view(), name='register'),
    re_path('active/(?P<token>.*)', ActiveView.as_view(), name='active'),
    path('login', LoginView.as_view(), name='login'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('user', UserInfoView.as_view(), name='user'),
    path('order/<int:page>', UserOrderView.as_view(), name='order'),
    path('address', AddressView.as_view(), name='address'),
]
