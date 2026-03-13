from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'service-prices', views.ServicePriceViewSet, basename='service-price')

urlpatterns = [
    path('price/', views.udc_price),
    path('request-document/', views.udc_request_document),
    path('verify/', views.udk_verify),
    path('my-certificates/', views.my_udk_certificates),
    path('certificates/<int:certificate_id>/download/', views.udk_certificate_download),
    path('root/', views.udc_root),
    path('children/', views.udc_children),
    path('search/', views.udc_search),
    # UDK Request endpoints (DOI kabi workflow)
    path('requests/', views.udk_request_list),  # GET - ro'yxat
    path('request/', views.udk_request_create),  # POST - yangi so'rov
    path('requests/<uuid:pk>/complete/', views.udk_request_complete),  # PATCH - yakunlash
    path('requests/<uuid:pk>/reject/', views.udk_request_reject),  # PATCH - rad etish
    # Service prices (bosh admin uchun)
    path('', include(router.urls)),
]
