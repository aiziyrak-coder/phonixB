from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categories', views.JournalCategoryViewSet, basename='category')
router.register('journals', views.JournalViewSet, basename='journal')
router.register('issues', views.IssueViewSet, basename='issue')

urlpatterns = [
    path('', include(router.urls)),
]
