from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import author_report_pdf

router = DefaultRouter()
router.register('', views.ArticleViewSet, basename='article')
doi_router = DefaultRouter()
doi_router.register('', views.DoiRequestViewSet, basename='doi-request')
article_sample_router = DefaultRouter()
article_sample_router.register('', views.ArticleSampleRequestViewSet, basename='article-sample-request')

urlpatterns = [
    path(
        'reports/author-malumotnoma.pdf',
        author_report_pdf.author_ma_lumotnoma_pdf,
        name='author_ma_lumotnoma_pdf',
    ),
    path(
        'reports/author-malumotnoma-signed-url/',
        author_report_pdf.author_ma_lumotnoma_signed_url,
    ),
    path('public/<uuid:pk>/', views.public_article_detail, name='public_article_detail'),
    path('article-sample/price/', views.article_sample_price),
    path('article-sample/request/', views.article_sample_request_create),
    path('article-sample/requests/', include(article_sample_router.urls)),
    path('doi/price/', views.doi_price),
    path('doi/request/', views.doi_request_create),
    path('doi/requests/', include(doi_router.urls)),
    path('', include(router.urls)),
]
