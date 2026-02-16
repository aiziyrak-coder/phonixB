#!/bin/bash
# Check Click callback logs and test endpoint

cd /phonix/backend

echo "=== Click Callback Tekshirish ==="
echo ""

echo "1. So'nggi Click prepare callback'larni ko'rish..."
sudo tail -100 /phonix/backend/logs/gunicorn-access.log | grep -i "click/prepare" | tail -10

echo ""
echo "2. So'nggi Click xatoliklarni ko'rish..."
sudo tail -100 /phonix/backend/logs/gunicorn-error.log | grep -i "click\|prepare\|signature" | tail -20

echo ""
echo "3. Click prepare endpoint'ni test qilish..."
curl -X POST https://api.ilmiyfaoliyat.uz/api/v1/payments/click/prepare/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "click_trans_id=123456&service_id=89248&merchant_trans_id=test-123&amount=1000&action=0&sign_time=2026-02-13&sign_string=test" \
  2>&1 | head -20

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

# So'nggi 10 daqiqadagi transaction'lar
recent = timezone.now() - timedelta(minutes=10)
transactions = Transaction.objects.filter(created_at__gte=recent).order_by('-created_at')[:5]

print("So'nggi 10 daqiqadagi transaction'lar:")
for t in transactions:
    print(f"  ID: {t.id}")
    print(f"  Status: {t.status}")
    print(f"  Amount: {t.amount}")
    print(f"  Click Trans ID: {t.click_trans_id or 'YO\'Q'}")
    print(f"  Click Service ID: {t.click_service_id or 'YO\'Q'}")
    print(f"  Created: {t.created_at}")
    print("")
EOF

echo ""
echo "=== Tekshirish yakunlandi ==="
