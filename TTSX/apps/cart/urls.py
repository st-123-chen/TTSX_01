from django.urls import path, include
from .views import CartAddView, CartInfoView, CartUpadteView, CartDeleteView

urlpatterns = [
    path('add', CartAddView.as_view(), name='add'),
    path('', CartInfoView.as_view(), name='show'),
    path('update', CartUpadteView.as_view(), name='update'),
    path('delete', CartDeleteView.as_view(), name='delete')

]
