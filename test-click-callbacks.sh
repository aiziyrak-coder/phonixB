#!/bin/bash
# Test Click callback endpoints to ensure they're accessible

echo "=== Testing Click Callback Endpoints ==="
echo ""

API_URL="https://api.ilmiyfaoliyat.uz"

echo "1. Testing Click prepare endpoint (GET for URL validation)..."
echo "----------------------------------------"
curl -X GET "${API_URL}/api/v1/payments/click/prepare/" \
  -v 2>&1 | grep -E "(< HTTP|status|message)" || echo "GET test failed"
echo ""

echo "2. Testing Click complete endpoint (GET for URL validation)..."
echo "----------------------------------------"
curl -X GET "${API_URL}/api/v1/payments/click/complete/" \
  -v 2>&1 | grep -E "(< HTTP|status|message)" || echo "GET test failed"
echo ""

echo "3. Testing Click prepare endpoint (POST with test data)..."
echo "----------------------------------------"
# Test prepare callback with sample data
PREPARE_DATA='{
  "click_trans_id": "1234567890",
  "service_id": "82154",
  "merchant_trans_id": "e25e01e1-5138-4238-a00e-e992c575c7b8",
  "amount": "1000",
  "action": "1",
  "sign_time": "1234567890",
  "sign_string": "test_signature"
}'

curl -X POST "${API_URL}/api/v1/payments/click/prepare/" \
  -H "Content-Type: application/json" \
  -d "$PREPARE_DATA" \
  -v 2>&1 | grep -E "(< HTTP|error|error_note|signature)" || echo "POST test failed"
echo ""

echo "4. Testing direct backend connection (port 8003)..."
echo "----------------------------------------"
curl -X GET "http://127.0.0.1:8003/api/v1/payments/click/prepare/" \
  -v 2>&1 | grep -E "(< HTTP|status|message)" || echo "Direct backend test failed"
echo ""

echo "5. Checking Nginx configuration for Click callbacks..."
echo "----------------------------------------"
if [ -f /etc/nginx/sites-available/api-ilmiyfaoliyat.conf ]; then
    echo "Nginx config contains Click callback routes:"
    grep -A 5 "click/prepare\|click/complete" /etc/nginx/sites-available/api-ilmiyfaoliyat.conf || echo "  No specific Click callback configuration found"
else
    echo "Nginx config file not found"
fi
echo ""

echo "6. Checking recent Click callback logs..."
echo "----------------------------------------"
tail -30 /phonix/backend/logs/gunicorn-access.log | grep -i "click" || echo "No recent Click callback requests in access log"
echo ""

echo "=== Test Complete ==="
echo ""
echo "Expected results:"
echo "  - GET requests should return 200 with status message"
echo "  - POST requests should return error (signature validation) but endpoint should be accessible"
echo "  - Direct backend connection should work"
echo ""
echo "If callbacks are not working, check:"
echo "  1. Click merchant panel callback URL configuration"
echo "  2. Nginx is proxying requests correctly"
echo "  3. Backend service is running and accessible"
