from django.contrib import admin
from .models import OrderGoods,OrderInfo
# Register your models here.
admin.site.register(OrderInfo)
admin.site.register(OrderGoods)
