#!/bin/bash
# Check payment error for specific transaction

echo "=== Checking Payment Error ==="
echo ""

cd /phonix/backend
source venv/bin/activate

# Transaction ID from the error
TRANSACTION_ID="e25e01e1-5138-4238-a00e-e992c575c7b8"
INVOICE_ID="176532873"
SERVICE_ID="82154"

echo "1. Checking transaction in database..."
echo "----------------------------------------"
python manage.py shell << EOF
from apps.payments.models import Transaction
from apps.users.models import User

try:
    transaction = Transaction.objects.get(id='${TRANSACTION_ID}')
    print(f"Transaction found:")
    print(f"  ID: {transaction.id}")
    print(f"  User: {transaction.user.phone if transaction.user else 'None'}")
    print(f"  Amount: {transaction.amount} {transaction.currency}")
    print(f"  Service Type: {transaction.service_type}")
    print(f"  Status: {transaction.status}")
    print(f"  Click Trans ID: {transaction.click_trans_id}")
    print(f"  Click Paydoc ID: {transaction.click_paydoc_id}")
    print(f"  Merchant Trans ID: {transaction.merchant_trans_id}")
    print(f"  Created: {transaction.created_at}")
    print(f"  Completed: {transaction.completed_at}")
except Transaction.DoesNotExist:
    print(f"❌ Transaction ${TRANSACTION_ID} not found in database")
except Exception as e:
    print(f"❌ Error: {e}")
EOF

echo ""
echo "2. Checking Click payment service configuration..."
echo "----------------------------------------"
python manage.py shell << 'EOF'
from django.conf import settings

print("Click Payment Configuration:")
print(f"  CLICK_MERCHANT_ID: {getattr(settings, 'CLICK_MERCHANT_ID', 'Not set')}")
print(f"  CLICK_SERVICE_ID: {getattr(settings, 'CLICK_SERVICE_ID', 'Not set')}")
print(f"  CLICK_SECRET_KEY: {'*' * 10 if getattr(settings, 'CLICK_SECRET_KEY', None) else 'Not set'}")
print(f"  CLICK_MERCHANT_USER_ID: {getattr(settings, 'CLICK_MERCHANT_USER_ID', 'Not set')}")
EOF

echo ""
echo "3. Testing Click invoice status check..."
echo "----------------------------------------"
python manage.py shell << EOF
from apps.payments.services import ClickPaymentService

service = ClickPaymentService()
result = service.check_invoice_status('${SERVICE_ID}', '${INVOICE_ID}')
print(f"Invoice status result: {result}")
EOF

echo ""
echo "4. Checking recent payment errors in logs..."
echo "----------------------------------------"
tail -50 /phonix/backend/logs/gunicorn-error.log | grep -i "payment\|click\|invoice\|error" | tail -20 || echo "No recent payment errors in logs"

echo ""
echo "=== Check Complete ==="
