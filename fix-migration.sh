#!/bin/bash
# Fix missing click_service_id column in database

cd /phonix/backend
source venv/bin/activate

echo "=== Migration yaratish va qo'llash ==="
echo ""

# Migration yaratish
echo "1. Migration yaratilmoqda..."
python manage.py makemigrations payments

# Migration qo'llash
echo ""
echo "2. Migration qo'llanmoqda..."
python manage.py migrate payments

echo ""
echo "✅ Migration muvaffaqiyatli yakunlandi!"

# Backend'ni restart qilish
echo ""
echo "3. Backend'ni restart qilish..."
sudo systemctl restart phoenix-backend

echo ""
echo "✅ Barcha o'zgarishlar qo'llandi!"
