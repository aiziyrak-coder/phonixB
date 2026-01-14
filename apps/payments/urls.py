from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('transactions', views.TransactionViewSet, basename='transaction')

urlpatterns = [
    # Click callbacks - both with and without trailing slash
    path('click/prepare/', views.click_prepare_view, name='click_prepare'),
    path('click/prepare', views.click_prepare_view, name='click_prepare_no_slash'),
    path('click/complete/', views.click_complete_view, name='click_complete'),
    path('click/complete', views.click_complete_view, name='click_complete_no_slash'),
    path('click/callback/', views.ClickPaymentView.as_view(), name='click_callback'),
    path('', include(router.urls)),
]