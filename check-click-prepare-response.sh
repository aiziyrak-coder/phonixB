#!/bin/bash
# Check Click prepare callback response

cd /phonix/backend

echo "=== Click Prepare Callback Response Tekshirish ==="
echo ""

echo "1. So'nggi Click prepare callback'larini ko'rish..."
sudo tail -50 /phonix/backend/logs/gunicorn-access.log | grep -i "click/prepare" | tail -5

echo ""
echo "2. So'nggi Click prepare xatoliklarni ko'rish..."
sudo tail -100 /phonix/backend/logs/gunicorn-error.log | grep -i "click\|prepare\|signature" | tail -20

echo ""
echo "3. Transaction'ni tekshirish..."
source venv/bin/activate
python manage.py shell << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.payments.models import Transaction

# So'nggi transaction'ni topish
tx = Transaction.objects.order_by('-created_at').first()
if tx:
    print(f"Oxirgi Transaction:")
    print(f"  ID: {tx.id}")
    print(f"  Status: {tx.status}")
    print(f"  Amount: {tx.amount}")
    print(f"  Click Trans ID: {tx.click_trans_id or 'YO\'Q'}")
    print(f"  Click Service ID: {tx.click_service_id or 'YO\'Q'}")
    print(f"  Merchant Trans ID: {tx.merchant_trans_id or 'YO\'Q'}")
    print(f"  Created: {tx.created_at}")
else:
    print("Transaction topilmadi")
EOF

echo ""
echo "=== Tekshirish yakunlandi ==="
