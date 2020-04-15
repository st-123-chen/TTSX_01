from celery import Celery
from django.shortcuts import render, redirect
from apps.goods.models import GoodsType, IndexGoodsBanner, IndexPromotionBanner, IndexTypeGoodsBanner
import re
import os
from django.urls import reverse
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from django.conf import settings
from itsdangerous import SignatureExpired
from django.http import HttpResponse
from django.core.mail import send_mail
from django.template import loader, RequestContext


# import django
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TTXS.settings')
# django.setup()
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'TTSX.settings')
#
# app = Celery('celery_tasks.tasks',broker='redis://127.0.0.1:6379/1')
#
# @app.task
# def send_reister_active_email(to_email,username,token):
#     #发送激活邮件
#     subject = '天天生鲜欢迎'  # 主题
#     message = ''  # 正文
#     sender = settings.EMAIL_FROM  # 发件人
#     receiver = [to_email]  # 收件人列表
#     html_message = '<h1>%s,欢迎使用守望先锋</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s<a/>' % (
#     username, token, token)
#     send_mail(subject, message=message, from_email=sender, recipient_list=receiver, html_message=html_message)
#     # subject = '天天生鲜欢迎'  #主题
#     # message = ''  #正文
#     # sender = settings.EMAIL_FROM    #发件人
#     # receiver = [email]      #收件人列表
#     # html_message = '<h1>%s,欢迎使用守望先锋</h1>请点击下面链接激活您的账户<br/><a href="http://127.0.0.1:8000/user/active/%s">http://127.0.0.1:8000/user/active/%s<a/>' %(username,token,token)
#     # send_mail(subject,message,sender,receiver,html_message=html_message)


# @app.task
def generate_static_index_html():
    # 产生首页静态页面
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

    # return render(request, 'static_index.html', context)
    # 1.加载模板文件
    temp = loader.get_template('static_index.html')
    # 2.定义模板上下文
    # context = RequestContext(request,context)
    # 3.模板渲染
    static_index_html = temp.render(context)

    # 生成首页静态页面
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    with open(save_path, 'w') as f:
        f.write(static_index_html)
