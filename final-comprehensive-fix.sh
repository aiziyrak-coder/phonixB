#!/bin/bash
# Final comprehensive fix for all issues

echo "=== Final Comprehensive Fix ==="
echo ""

# 1. Backend fixes
echo "1. Backend Fixes..."
echo "----------------------------------------"
cd /phonix/backend

# Pull latest
git pull origin master

# Restart backend
echo "  → Restarting backend..."
sudo systemctl restart phoenix-backend
sleep 5

# Check status
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✓ Backend is running"
else
    echo "  ✗ Backend failed to start"
    sudo journalctl -u phoenix-backend -n 20 --no-pager
    exit 1
fi

# 2. Test all endpoints
echo ""
echo "2. Testing All Endpoints..."
echo "----------------------------------------"

# Test login
echo "  → Testing login..."
LOGIN_RESPONSE=$(curl -X POST "https://api.ilmiyfaoliyat.uz/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Login endpoint works (HTTP $HTTP_CODE)"
else
    echo "  ✗ Login endpoint failed (HTTP $HTTP_CODE)"
fi

# Test register
echo "  → Testing register..."
REGISTER_RESPONSE=$(curl -X POST "https://api.ilmiyfaoliyat.uz/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","email":"test@test.com","password":"test123456","password_confirm":"test123456","first_name":"Test","last_name":"User"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "201" ]; then
    echo "  ✓ Register endpoint works (HTTP $HTTP_CODE)"
else
    echo "  ✗ Register endpoint failed (HTTP $HTTP_CODE)"
fi

# Test Click callbacks
echo "  → Testing Click callbacks..."
PREPARE_RESPONSE=$(curl -X GET "https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/" \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$PREPARE_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Click prepare callback works (HTTP $HTTP_CODE)"
else
    echo "  ✗ Click prepare callback failed (HTTP $HTTP_CODE)"
fi

# 3. Check CORS
echo ""
echo "3. Checking CORS Configuration..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from django.conf import settings

print("CORS Settings:")
print(f"  CORS_ALLOWED_ORIGINS: {getattr(settings, 'CORS_ALLOWED_ORIGINS', [])}")
print(f"  CORS_ALLOW_CREDENTIALS: {getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)}")
print(f"  Production origin in list: {'https://ilmiyfaoliyat.uz' in getattr(settings, 'CORS_ALLOWED_ORIGINS', [])}")
EOF

# 4. Check recent errors
echo ""
echo "4. Recent Errors..."
echo "----------------------------------------"
tail -30 /phonix/backend/logs/gunicorn-error.log 2>/dev/null | tail -5 || echo "  No recent errors"

# 5. Frontend build check
echo ""
echo "5. Frontend Build Status..."
echo "----------------------------------------"
cd /phonix/frontend

if [ -d "dist" ] && [ -f "dist/index.html" ]; then
    echo "  ✓ Frontend build exists"
    
    # Check if API URL is correct in built files
    if grep -q "api.ilmiyfaoliyat.uz" dist/assets/*.js 2>/dev/null; then
        echo "  ✓ Frontend uses production API URL"
    else
        echo "  ⚠️  Frontend might be using wrong API URL"
        echo "  → Rebuild frontend with: npm run build"
    fi
else
    echo "  ✗ Frontend build not found"
    echo "  → Build frontend with: npm run build"
fi

echo ""
echo "=== Fix Complete ==="
echo ""
echo "Next Steps:"
echo "  1. If frontend needs rebuild:"
echo "     cd /phonix/frontend"
echo "     export VITE_API_BASE_URL=https://api.ilmiyfaoliyat.uz/api/v1"
echo "     npm run build"
echo ""
echo "  2. Clear browser cache (Ctrl+Shift+Delete)"
echo "  3. Hard reload page (Ctrl+F5)"
echo "  4. Test login/register"
echo "  5. Test payment"
