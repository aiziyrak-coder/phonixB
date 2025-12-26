from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    path('click/prepare/', views.click_prepare_view, name='click_prepare'),
    path('click/complete/', views.click_complete_view, name='click_complete'),
    path('click/callback/', views.ClickPaymentView.as_view(), name='click_callback'),
    path('', include(router.urls)),
]