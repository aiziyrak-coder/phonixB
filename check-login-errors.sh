#!/bin/bash
# Check login errors from gunicorn logs

echo "=== Checking Login Errors ==="
echo ""

# Check gunicorn error log
ERROR_LOG="/phonix/backend/logs/gunicorn-error.log"
if [ -f "$ERROR_LOG" ]; then
    echo "Recent errors from gunicorn-error.log:"
    echo "----------------------------------------"
    tail -50 "$ERROR_LOG" | grep -i "login\|error\|exception\|traceback" || tail -30 "$ERROR_LOG"
    echo ""
else
    echo "Error log not found at $ERROR_LOG"
fi

# Check access log for login requests
ACCESS_LOG="/phonix/backend/logs/gunicorn-access.log"
if [ -f "$ACCESS_LOG" ]; then
    echo "Recent login requests from gunicorn-access.log:"
    echo "----------------------------------------"
    tail -20 "$ACCESS_LOG" | grep -i "login\|auth" || tail -10 "$ACCESS_LOG"
    echo ""
else
    echo "Access log not found at $ACCESS_LOG"
fi

# Test login endpoint directly
echo "Testing login endpoint directly:"
echo "----------------------------------------"
curl -X POST http://127.0.0.1:8003/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"phone":"998901234567","password":"test123"}' \
  -v 2>&1 | grep -E "(< HTTP|error|detail|phone|password|access)" || echo "Connection test completed"

echo ""
echo "=== Check Complete ==="
