#!/bin/bash
# Debug Click prepare callback

cd /phonix/backend

echo "=== Click Prepare Callback Debug ==="
echo ""

echo "1. So'nggi Click prepare POST request'lari..."
sudo tail -100 /phonix/backend/logs/gunicorn-access.log | grep "POST.*click/prepare" | tail -5

echo ""
echo "2. So'nggi Click prepare response'lari..."
sudo tail -200 /phonix/backend/logs/gunicorn-access.log | grep -A 1 "POST.*click/prepare" | grep -E "200|400|500" | tail -5

echo ""
echo "3. So'nggi Click xatoliklari..."
sudo tail -100 /phonix/backend/logs/gunicorn-error.log | grep -i "click\|prepare\|signature" | tail -20

echo ""
echo "4. Transaction'ni tekshirish..."
source venv/bin/activate
python manage.py shell << 'EOF'
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()

from apps.payments.models import Transaction
from django.utils import timezone
from datetime import timedelta

# So'nggi 5 daqiqadagi transaction'lar
recent = timezone.now() - timedelta(minutes=5)
txs = Transaction.objects.filter(created_at__gte=recent).order_by('-created_at')[:3]

print("So'nggi 5 daqiqadagi transaction'lar:")
for tx in txs:
    print(f"\nTransaction ID: {tx.id}")
    print(f"  Status: {tx.status}")
    print(f"  Amount: {tx.amount}")
    print(f"  Click Trans ID: {tx.click_trans_id or 'YO\'Q'}")
    print(f"  Click Service ID: {tx.click_service_id or 'YO\'Q'}")
    print(f"  Merchant Trans ID: {tx.merchant_trans_id or 'YO\'Q'}")
    print(f"  Created: {tx.created_at}")
EOF

echo ""
echo "=== Debug yakunlandi ==="
