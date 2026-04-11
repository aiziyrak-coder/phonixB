"""
URL configuration for Phoenix Scientific Platform
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .jwt_views import CookieTokenRefreshView
from .health import health_live, health_ready, metrics_prometheus
from .github_deploy_webhook import github_deploy_webhook

urlpatterns = [
    path('health/', health_live),
    path('health/live/', health_live),
    path('health/ready/', health_ready),
    path('metrics/', metrics_prometheus),
    # GitHub Webhooks → deploy (GITHUB_DEPLOY_WEBHOOK_SECRET .env da bo‘lganda ishlaydi)
    path('hooks/github/deploy/', github_deploy_webhook),
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/auth/', include('apps.users.urls')),
    path('api/v1/articles/', include('apps.articles.urls')),
    path('api/v1/journals/', include('apps.journals.urls')),
    path('api/v1/payments/', include('apps.payments.urls')),
    path('api/v1/translations/', include('apps.translations.urls')),
    path('api/v1/reviews/', include('apps.reviews.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),
    path('api/v1/udc/', include('apps.udc.urls')),
    
    # JWT token refresh
    path('api/v1/token/refresh/', CookieTokenRefreshView.as_view(), name='token_refresh'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Admin site customization
admin.site.site_header = "Phoenix Scientific Platform Admin"
admin.site.site_title = "Phoenix Scientific"
admin.site.index_title = "Welcome to Phoenix Scientific Platform"
