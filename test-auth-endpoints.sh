#!/bin/bash
# Test login and register endpoints to identify connection issues

echo "=== Testing Auth Endpoints ==="
echo ""

API_URL="https://api.ilmiyfaoliyat.uz"
ORIGIN="https://ilmiyfaoliyat.uz"

echo "1. Testing OPTIONS preflight for login..."
echo "----------------------------------------"
curl -X OPTIONS "${API_URL}/api/v1/auth/login/" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v 2>&1 | grep -E "(< HTTP|Access-Control|OPTIONS)" || echo "OPTIONS test failed"
echo ""

echo "2. Testing OPTIONS preflight for register..."
echo "----------------------------------------"
curl -X OPTIONS "${API_URL}/api/v1/auth/register/" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type" \
  -v 2>&1 | grep -E "(< HTTP|Access-Control|OPTIONS)" || echo "OPTIONS test failed"
echo ""

echo "3. Testing login endpoint (should return 400 for invalid credentials)..."
echo "----------------------------------------"
LOGIN_RESPONSE=$(curl -X POST "${API_URL}/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -H "Origin: ${ORIGIN}" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

echo "$LOGIN_RESPONSE"
HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP Status: $HTTP_CODE"
echo ""

echo "4. Testing register endpoint (should return 400 for invalid data)..."
echo "----------------------------------------"
REGISTER_RESPONSE=$(curl -X POST "${API_URL}/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -H "Origin: ${ORIGIN}" \
  -d '{"phone":"998901234567","email":"test@test.com","password":"test123","password_confirm":"test123","first_name":"Test","last_name":"User"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

echo "$REGISTER_RESPONSE"
HTTP_CODE=$(echo "$REGISTER_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP Status: $HTTP_CODE"
echo ""

echo "5. Testing direct backend connection (port 8003)..."
echo "----------------------------------------"
DIRECT_RESPONSE=$(curl -X POST "http://127.0.0.1:8003/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

echo "$DIRECT_RESPONSE"
HTTP_CODE=$(echo "$DIRECT_RESPONSE" | grep "HTTP_CODE" | cut -d: -f2)
echo "HTTP Status: $HTTP_CODE"
echo ""

echo "6. Checking backend service status..."
echo "----------------------------------------"
sudo systemctl status phoenix-backend --no-pager -l | head -15
echo ""

echo "7. Checking Nginx status..."
echo "----------------------------------------"
sudo systemctl status nginx --no-pager -l | head -10
echo ""

echo "=== Test Complete ==="
echo ""
echo "Expected results:"
echo "  - OPTIONS requests should return 204 with CORS headers"
echo "  - Login/Register should return 400 (validation error) or 201/200 (success)"
echo "  - Direct backend connection should work"
echo "  - Backend service should be active (running)"
