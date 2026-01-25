#!/bin/bash
# Test login API endpoint to debug 400 Bad Request

echo "=== Testing Login API ==="
echo ""

# Test 1: Simple login request
echo "Test 1: Basic login request"
curl -X POST https://api.ilmiyfaoliyat.uz/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -H "Origin: https://ilmiyfaoliyat.uz" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -v 2>&1 | grep -E "(< HTTP|error|detail|phone|password)"

echo ""
echo "=== Test Complete ==="
