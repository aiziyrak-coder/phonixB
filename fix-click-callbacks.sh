#!/bin/bash
# Fix Click payment callbacks - ensure callbacks are being received

echo "=== Fixing Click Payment Callbacks ==="
echo ""

cd /phonix/backend
source venv/bin/activate

# 1. Check if callback URLs are accessible from outside
echo "1. Testing Callback URL Accessibility..."
echo "----------------------------------------"
echo "  → Testing prepare callback URL..."
PREPARE_TEST=$(curl -X GET "https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/" \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$PREPARE_TEST" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Prepare callback URL is accessible (HTTP 200)"
else
    echo "  ✗ Prepare callback URL returned HTTP $HTTP_CODE"
fi

echo "  → Testing complete callback URL..."
COMPLETE_TEST=$(curl -X GET "https://api.ilmiyfaoliyat.uz/api/v1/payments/click/complete/" \
  -w "\nHTTP_CODE:%{http_code}" \
  -s 2>&1)

HTTP_CODE=$(echo "$COMPLETE_TEST" | grep "HTTP_CODE" | cut -d: -f2)
if [ "$HTTP_CODE" = "200" ]; then
    echo "  ✓ Complete callback URL is accessible (HTTP 200)"
else
    echo "  ✗ Complete callback URL returned HTTP $HTTP_CODE"
fi
echo ""

# 2. Check recent Click callback requests
echo "2. Recent Click Callback Requests..."
echo "----------------------------------------"
echo "  → Checking access logs for Click callbacks..."
tail -100 /phonix/backend/logs/gunicorn-access.log 2>/dev/null | grep -i "click/prepare\|click/complete" | tail -10 || echo "  No recent Click callback requests found"
echo ""

# 3. Check transaction status and provide callback URLs
echo "3. Click Merchant Panel Configuration..."
echo "----------------------------------------"
echo "  → Required Callback URLs for Click Merchant Panel:"
echo ""
echo "  Prepare Callback URL:"
echo "    https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/"
echo ""
echo "  Complete Callback URL:"
echo "    https://api.ilmiyfaoliyat.uz/api/v1/payments/click/complete/"
echo ""
echo "  → Instructions:"
echo "    1. Login to merchant.click.uz"
echo "    2. Go to Service Settings"
echo "    3. Set Prepare Callback URL to: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/"
echo "    4. Set Complete Callback URL to: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/complete/"
echo "    5. Save settings"
echo ""

# 4. Check if transactions are waiting for callbacks
echo "4. Pending Transactions Waiting for Callbacks..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from apps.payments.models import Transaction
from django.utils import timezone
from datetime import timedelta

pending = Transaction.objects.filter(
    status='pending',
    created_at__gte=timezone.now() - timedelta(hours=24),
    click_trans_id__isnull=True
).order_by('-created_at')

print(f"Pending transactions without Click callbacks: {pending.count()}")
for t in pending[:5]:
    print(f"  - Transaction ID: {t.id}")
    print(f"    User: {t.user.phone if t.user else 'None'}")
    print(f"    Amount: {t.amount} {t.currency}")
    print(f"    Created: {t.created_at}")
    print(f"    Age: {(timezone.now() - t.created_at).total_seconds() / 60:.1f} minutes")
    print("")
EOF

# 5. Test invoice creation
echo "5. Testing Invoice Creation..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from apps.payments.services import ClickPaymentService
from apps.payments.models import Transaction

# Get a recent pending transaction
recent_tx = Transaction.objects.filter(status='pending').order_by('-created_at').first()

if recent_tx:
    print(f"Testing invoice creation for transaction: {recent_tx.id}")
    service = ClickPaymentService()
    
    # Try to prepare payment (creates invoice)
    result = service.prepare_payment(recent_tx)
    
    print(f"Result:")
    print(f"  Error Code: {result.get('error_code')}")
    print(f"  Error Note: {result.get('error_note')}")
    print(f"  Payment URL: {result.get('payment_url')}")
    print(f"  Invoice ID: {result.get('invoice_id')}")
    
    if result.get('error_code') == 0:
        print("  ✓ Invoice created successfully")
    else:
        print(f"  ✗ Invoice creation failed: {result.get('error_note')}")
else:
    print("  No pending transactions found for testing")
EOF

echo ""
echo "=== Fix Complete ==="
echo ""
echo "IMPORTANT: Configure Click Merchant Panel with callback URLs:"
echo "  Prepare: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/"
echo "  Complete: https://api.ilmiyfaoliyat.uz/api/v1/payments/click/complete/"
