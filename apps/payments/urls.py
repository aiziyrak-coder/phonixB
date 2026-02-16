from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='transaction')

# Payment provider callbacks must be BEFORE router.urls to avoid conflicts
urlpatterns = [
    # Click callbacks - both with and without trailing slash
    # Click merchant panel validation uchun trailing slash'siz ham qo'llab-quvvatlash
    re_path(r'^click/prepare/?$', views.click_prepare_view, name='click_prepare'),
    re_path(r'^click/complete/?$', views.click_complete_view, name='click_complete'),
    re_path(r'^click/callback/?$', views.ClickPaymentView.as_view(), name='click_callback'),
    
    # Payme callback - JSON-RPC endpoint
    re_path(r'^payme/?$', views.payme_callback_view, name='payme_callback'),
    
    # Router URLs come after payment provider URLs
    path('', include(router.urls)),
]