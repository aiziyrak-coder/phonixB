#!/bin/bash
# Comprehensive diagnosis of all issues: login, register, and payment

echo "=== Comprehensive Diagnosis ==="
echo ""

cd /phonix/backend
source venv/bin/activate

# 1. Check backend service
echo "1. Backend Service Status..."
echo "----------------------------------------"
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✓ Backend service is running"
    sudo systemctl status phoenix-backend --no-pager -l | head -5
else
    echo "  ✗ Backend service is NOT running"
    sudo journalctl -u phoenix-backend -n 10 --no-pager
fi
echo ""

# 2. Check backend port
echo "2. Backend Port Status..."
echo "----------------------------------------"
if sudo lsof -ti:8003 >/dev/null 2>&1; then
    PORT_PID=$(sudo lsof -ti:8003 | head -1)
    echo "  ✓ Port 8003 is in use (PID: $PORT_PID)"
    ps -p $PORT_PID -o cmd= | head -1
else
    echo "  ✗ Port 8003 is NOT in use"
fi
echo ""

# 3. Test login endpoint
echo "3. Testing Login Endpoint..."
echo "----------------------------------------"
LOGIN_TEST=$(curl -X POST "https://api.ilmiyfaoliyat.uz/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$LOGIN_TEST" | grep "HTTP_CODE" | cut -d: -f2)
RESPONSE=$(echo "$LOGIN_TEST" | grep -v "HTTP_CODE")

if [ "$HTTP_CODE" = "400" ]; then
    echo "  ✓ Login endpoint is accessible (HTTP 400 - validation error, expected)"
    echo "  Response: $RESPONSE"
elif [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Login endpoint is accessible (HTTP 200 - success)"
else
    echo "  ✗ Login endpoint returned HTTP $HTTP_CODE"
    echo "  Response: $RESPONSE"
fi
echo ""

# 4. Test register endpoint
echo "4. Testing Register Endpoint..."
echo "----------------------------------------"
REGISTER_TEST=$(curl -X POST "https://api.ilmiyfaoliyat.uz/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","email":"test@test.com","password":"test123","password_confirm":"test123","first_name":"Test","last_name":"User"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$REGISTER_TEST" | grep "HTTP_CODE" | cut -d: -f2)
RESPONSE=$(echo "$REGISTER_TEST" | grep -v "HTTP_CODE")

if [ "$HTTP_CODE" = "400" ]; then
    echo "  ✓ Register endpoint is accessible (HTTP 400 - validation error, expected)"
    echo "  Response: $RESPONSE"
elif [ "$HTTP_CODE" = "201" ]; then
    echo "  ✓ Register endpoint is accessible (HTTP 201 - success)"
else
    echo "  ⚠️  Register endpoint returned HTTP $HTTP_CODE"
    echo "  Response: $RESPONSE"
fi
echo ""

# 5. Check recent transactions
echo "5. Recent Transactions..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from apps.payments.models import Transaction
from django.utils import timezone
from datetime import timedelta

recent = Transaction.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=24)
).order_by('-created_at')[:5]

print(f"Recent transactions (last 24 hours): {recent.count()}")
for t in recent:
    print(f"  - ID: {t.id}")
    print(f"    User: {t.user.phone if t.user else 'None'}")
    print(f"    Amount: {t.amount} {t.currency}")
    print(f"    Status: {t.status}")
    print(f"    Click Trans ID: {t.click_trans_id or 'None'}")
    print(f"    Created: {t.created_at}")
    print("")
EOF

# 6. Check Click configuration
echo "6. Click Payment Configuration..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from django.conf import settings

print("Click Settings:")
print(f"  CLICK_MERCHANT_ID: {getattr(settings, 'CLICK_MERCHANT_ID', 'Not set')}")
print(f"  CLICK_SERVICE_ID: {getattr(settings, 'CLICK_SERVICE_ID', 'Not set')}")
print(f"  CLICK_SECRET_KEY: {'Set' if getattr(settings, 'CLICK_SECRET_KEY', None) else 'Not set'}")
print(f"  CLICK_MERCHANT_USER_ID: {getattr(settings, 'CLICK_MERCHANT_USER_ID', 'Not set')}")
EOF

echo ""

# 7. Check CORS settings
echo "7. CORS Configuration..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from django.conf import settings

print("CORS Settings:")
print(f"  CORS_ALLOWED_ORIGINS: {getattr(settings, 'CORS_ALLOWED_ORIGINS', [])}")
print(f"  CORS_ALLOW_CREDENTIALS: {getattr(settings, 'CORS_ALLOW_CREDENTIALS', False)}")
print(f"  CORS middleware in MIDDLEWARE: {'corsheaders.middleware.CorsMiddleware' in getattr(settings, 'MIDDLEWARE', [])}")
EOF

echo ""

# 8. Check Nginx status
echo "8. Nginx Status..."
echo "----------------------------------------"
if sudo systemctl is-active --quiet nginx; then
    echo "  ✓ Nginx is running"
else
    echo "  ✗ Nginx is NOT running"
fi
echo ""

# 9. Check recent errors
echo "9. Recent Backend Errors..."
echo "----------------------------------------"
tail -20 /phonix/backend/logs/gunicorn-error.log 2>/dev/null | grep -i "error\|exception" | tail -5 || echo "  No recent errors in log file"

echo ""
echo "=== Diagnosis Complete ==="
echo ""
echo "Summary:"
echo "  - Check if backend service is running"
echo "  - Check if endpoints are accessible"
echo "  - Check transaction status"
echo "  - Check Click configuration"
echo "  - Check CORS settings"
