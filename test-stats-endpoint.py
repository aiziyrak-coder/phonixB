import os
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_local')
django.setup()

from rest_framework.routers import DefaultRouter
from apps.users.views import UserViewSet

# Create router and register viewset
router = DefaultRouter()
router.register('', UserViewSet, basename='user')

# Print all registered URLs
print("Registered URLs:")
for route in router.urls:
    print(f"  Pattern: {route.pattern}")
    print(f"  Name: {route.name}")
    print(f"  Methods: {getattr(route, 'methods', 'N/A')}")
    print()