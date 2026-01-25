#!/bin/bash
# Fix Django CORS middleware to ensure OPTIONS preflight works correctly

echo "=== Fixing Django CORS Middleware ==="
echo ""

cd /phonix/backend
source venv/bin/activate

echo "1. Checking CORS middleware configuration..."
python manage.py shell << 'EOF'
from django.conf import settings

print("=== Current CORS Settings ===")
print(f"CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}")
print(f"CORS_ALLOW_CREDENTIALS: {settings.CORS_ALLOW_CREDENTIALS}")
print(f"CORS_ALLOW_METHODS: {settings.CORS_ALLOW_METHODS}")
print(f"CORS_ALLOW_HEADERS: {settings.CORS_ALLOW_HEADERS}")

# Check middleware order
middleware_list = list(settings.MIDDLEWARE)
cors_index = None
for i, mw in enumerate(middleware_list):
    if 'cors' in mw.lower():
        cors_index = i
        print(f"\nCORS Middleware found at index {i}: {mw}")
        print(f"  Before: {middleware_list[i-1] if i > 0 else 'START'}")
        print(f"  After: {middleware_list[i+1] if i < len(middleware_list)-1 else 'END'}")

if cors_index is None:
    print("\n❌ ERROR: CORS middleware not found in MIDDLEWARE!")
else:
    print("\n✓ CORS middleware is in MIDDLEWARE")
    
    # Check if it's in the right position (should be early, after SessionMiddleware)
    if cors_index < 3:
        print("✓ CORS middleware is in correct position (early in middleware stack)")
    else:
        print("⚠️  WARNING: CORS middleware might be too late in middleware stack")
EOF

echo ""
echo "2. Testing OPTIONS request directly to Django..."
echo "----------------------------------------"
curl -X OPTIONS "http://127.0.0.1:8003/api/v1/auth/login/" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v 2>&1 | grep -E "(< HTTP|Access-Control|OPTIONS)" || echo "Direct Django test failed"
echo ""

echo "3. Checking Django CORS middleware response..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from django.test import RequestFactory
from django.http import JsonResponse
from corsheaders.middleware import CorsMiddleware
from django.middleware.common import CommonMiddleware

# Create a test request
factory = RequestFactory()
request = factory.options('/api/v1/auth/login/', 
    HTTP_ORIGIN='https://ilmiyfaoliyat.uz',
    HTTP_ACCESS_CONTROL_REQUEST_METHOD='POST',
    HTTP_ACCESS_CONTROL_REQUEST_HEADERS='Content-Type'
)

print("Test request created:")
print(f"  Method: {request.method}")
print(f"  Origin: {request.META.get('HTTP_ORIGIN', 'None')}")
print(f"  Access-Control-Request-Method: {request.META.get('HTTP_ACCESS_CONTROL_REQUEST_METHOD', 'None')}")

# Check if CORS middleware would process this
from django.conf import settings
from corsheaders.middleware import CorsMiddleware

middleware = CorsMiddleware(lambda req: JsonResponse({}))
response = middleware(request)

print(f"\nResponse status: {response.status_code}")
print(f"Response headers:")
for key, value in response.items():
    if 'access-control' in key.lower():
        print(f"  {key}: {value}")
EOF

echo ""
echo "=== CORS Middleware Check Complete ==="
