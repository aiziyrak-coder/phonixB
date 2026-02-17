from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('', views.ArticleViewSet, basename='article')

urlpatterns = [
    path('public/<uuid:pk>/', views.public_article_detail, name='public_article_detail'),
    path('', include(router.urls)),
]
