#!/bin/bash
# Test API connection and CORS settings

echo "=== API Connection Test ==="
echo ""

API_URL="https://api.ilmiyfaoliyat.uz/api/v1"

echo "1. Testing API endpoint: ${API_URL}/auth/register/"
echo ""

# Test CORS headers
echo "2. Testing CORS headers..."
curl -I -X OPTIONS "${API_URL}/auth/register/" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type" \
  2>&1 | grep -i "access-control"

echo ""
echo "3. Testing registration endpoint (should return validation error, not network error)..."
curl -X POST "${API_URL}/auth/register/" \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","password":"test123"}' \
  2>&1 | head -20

echo ""
echo "=== Test Complete ==="
