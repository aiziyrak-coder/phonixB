#!/bin/bash
# Test API from browser's perspective (with CORS headers)

echo "=== Testing from Browser Perspective ==="
echo ""

API_URL="https://api.ilmiyfaoliyat.uz"
ORIGIN="https://ilmiyfaoliyat.uz"

echo "1. Testing OPTIONS preflight (browser sends this first)..."
echo "----------------------------------------"
OPTIONS_RESPONSE=$(curl -X OPTIONS "${API_URL}/api/v1/auth/login/" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization" \
  -v 2>&1)

echo "$OPTIONS_RESPONSE" | grep -E "(< HTTP|Access-Control|OPTIONS)" || echo "OPTIONS test completed"
echo ""

echo "2. Testing actual POST request (like browser)..."
echo "----------------------------------------"
POST_RESPONSE=$(curl -X POST "${API_URL}/api/v1/auth/login/" \
  -H "Content-Type: application/json" \
  -H "Origin: ${ORIGIN}" \
  -H "Referer: ${ORIGIN}/" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -v 2>&1)

HTTP_CODE=$(echo "$POST_RESPONSE" | grep "< HTTP" | tail -1)
CORS_HEADERS=$(echo "$POST_RESPONSE" | grep -i "access-control")

echo "HTTP Status: $HTTP_CODE"
if [ -n "$CORS_HEADERS" ]; then
    echo "CORS Headers found:"
    echo "$CORS_HEADERS"
else
    echo "⚠️  No CORS headers in response"
fi

RESPONSE_BODY=$(echo "$POST_RESPONSE" | grep -A 100 "^{" | head -5)
echo "Response body: $RESPONSE_BODY"
echo ""

echo "3. Testing Register with proper headers..."
echo "----------------------------------------"
REGISTER_RESPONSE=$(curl -X POST "${API_URL}/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -H "Origin: ${ORIGIN}" \
  -H "Referer: ${ORIGIN}/" \
  -d '{"phone":"998901234568","email":"test'$(date +%s)'@test.com","password":"test123456","password_confirm":"test123456","first_name":"Test","last_name":"User"}' \
  -v 2>&1)

HTTP_CODE=$(echo "$REGISTER_RESPONSE" | grep "< HTTP" | tail -1)
CORS_HEADERS=$(echo "$REGISTER_RESPONSE" | grep -i "access-control")

echo "HTTP Status: $HTTP_CODE"
if [ -n "$CORS_HEADERS" ]; then
    echo "CORS Headers found:"
    echo "$CORS_HEADERS"
else
    echo "⚠️  No CORS headers in response"
fi

RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | grep -A 100 "^{" | head -5)
echo "Response body: $RESPONSE_BODY"
echo ""

echo "=== Test Complete ==="
echo ""
echo "If CORS headers are missing, the issue is with Django CORS middleware"
echo "If endpoints return errors, check the response body above"
