#!/bin/bash
# Comprehensive fix for all backend and frontend connection issues

echo "=== Comprehensive Fix for All Issues ==="
echo ""

# 1. Backend fixes
echo "1. Backend fixes..."
echo "----------------------------------------"
cd /phonix/backend

# Pull latest changes
echo "  → Pulling latest backend changes..."
git pull origin master

# Restart backend service
echo "  → Restarting backend service..."
sudo systemctl restart phoenix-backend
sleep 3

# Check backend status
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✓ Backend service is running"
else
    echo "  ✗ Backend service failed to start"
    sudo journalctl -u phoenix-backend -n 20 --no-pager
    exit 1
fi

# 2. Frontend fixes
echo ""
echo "2. Frontend fixes..."
echo "----------------------------------------"
cd /phonix/frontend

# Pull latest changes
echo "  → Pulling latest frontend changes..."
git pull origin master

# Set production environment variables
export VITE_API_BASE_URL=https://api.ilmiyfaoliyat.uz/api/v1
export VITE_MEDIA_URL=https://api.ilmiyfaoliyat.uz/media/
export VITE_ENV=production

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "  → Installing dependencies..."
    npm install
fi

# Build for production
echo "  → Building frontend for production..."
npm run build

if [ $? -eq 0 ]; then
    echo "  ✓ Frontend build successful"
else
    echo "  ✗ Frontend build failed"
    exit 1
fi

# 3. Nginx reload
echo ""
echo "3. Reloading Nginx..."
echo "----------------------------------------"
sudo systemctl reload nginx
if sudo systemctl is-active --quiet nginx; then
    echo "  ✓ Nginx reloaded"
else
    echo "  ✗ Nginx failed to reload"
    exit 1
fi

# 4. Test endpoints
echo ""
echo "4. Testing endpoints..."
echo "----------------------------------------"
echo "  → Testing login endpoint..."
LOGIN_TEST=$(curl -X POST "https://api.ilmiyfaoliyat.uz/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1 | tail -1)

HTTP_CODE=$(echo "$LOGIN_TEST" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "400" ] || [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Login endpoint is accessible (HTTP $HTTP_CODE)"
else
    echo "  ⚠️  Login endpoint returned HTTP $HTTP_CODE"
fi

echo ""
echo "=== Fix Complete ==="
echo ""
echo "Next steps:"
echo "  1. Clear browser cache (Ctrl+Shift+Delete)"
echo "  2. Hard reload the page (Ctrl+F5)"
echo "  3. Test login/register functionality"
echo "  4. Test payment functionality"
