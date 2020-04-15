from django.contrib import admin
from ..goods.models import GoodsType,IndexPromotionBanner,GoodsSKU,Goods,GoodsImage,IndexTypeGoodsBanner,IndexGoodsBanner
#Register your models here.
class IndexpromotionBannerAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()

    def delete_model(self, request, obj):
        super().delete_model(request, obj)
        from celery_tasks.tasks import generate_static_index_html
        generate_static_index_html.delay()



admin.site.register(GoodsType)
admin.site.register(IndexPromotionBanner)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
