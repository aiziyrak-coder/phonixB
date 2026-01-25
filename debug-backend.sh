#!/bin/bash
# Backend Debug Script
# Bu script backend service'ning nima uchun crash qilayotganini aniqlash uchun

set -e

echo "🔍 Backend service xatoliklarini tekshirish..."
echo ""

cd /phonix/backend

# 1. Virtual environment aktivlashtirish
echo "  → Virtual environment aktivlashtirish..."
source venv/bin/activate

# 2. Environment variables yuklash
echo "  → Environment variables yuklash..."
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "  ✅ .env fayl yuklandi"
else
    echo "  ⚠️  .env fayl topilmadi"
fi

# 3. Django check
echo ""
echo "  → Django check qilish..."
python manage.py check --deploy 2>&1 || echo "  ⚠️  Django check xatolik"

# 4. Settings import test
echo ""
echo "  → Settings import test..."
python -c "import django; django.setup(); from django.conf import settings; print('✅ Settings yuklandi'); print(f'CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}')" 2>&1 || echo "  ❌ Settings import xatolik"

# 5. Gunicorn manual test
echo ""
echo "  → Gunicorn manual test (5 soniya)..."
timeout 5 gunicorn --workers 1 --bind 127.0.0.1:8001 --timeout 10 config.wsgi:application 2>&1 || echo "  ⚠️  Gunicorn test tugadi (timeout yoki xatolik)"

# 6. Service logs ko'rish
echo ""
echo "  → Service logs (oxirgi 30 qator)..."
sudo journalctl -u phoenix-backend --no-pager -n 30 | tail -20

# 7. Gunicorn error log
echo ""
echo "  → Gunicorn error log (agar mavjud bo'lsa)..."
if [ -f logs/gunicorn-error.log ]; then
    tail -30 logs/gunicorn-error.log
else
    echo "  ⚠️  Gunicorn error log topilmadi"
fi

deactivate

echo ""
echo "✅ Debug yakunlandi!"
