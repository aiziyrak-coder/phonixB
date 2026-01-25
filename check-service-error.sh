#!/bin/bash
# Service Error Tekshirish Script

set -e

echo "🔍 Backend service xatoliklarini tekshirish..."
echo ""

cd /phonix/backend

# 1. Service'ni to'xtatish
echo "  → Service'ni to'xtatish..."
sudo systemctl stop phoenix-backend
sleep 2

# 2. Virtual environment aktivlashtirish
echo "  → Virtual environment aktivlashtirish..."
source venv/bin/activate

# 3. Environment variables yuklash
echo "  → Environment variables yuklash..."
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "  ✅ .env fayl yuklandi"
else
    echo "  ⚠️  .env fayl topilmadi"
fi

# 4. Django check
echo ""
echo "  → Django check qilish..."
python manage.py check 2>&1 | head -50

# 5. Settings import test
echo ""
echo "  → Settings import test..."
python -c "
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
try:
    django.setup()
    from django.conf import settings
    print('✅ Settings yuklandi')
    print(f'CORS_ALLOWED_ORIGINS: {settings.CORS_ALLOWED_ORIGINS}')
except Exception as e:
    print(f'❌ Settings import xatolik: {e}')
    import traceback
    traceback.print_exc()
" 2>&1

# 6. Gunicorn manual test (to'g'ridan-to'g'ri)
echo ""
echo "  → Gunicorn manual test (10 soniya)..."
timeout 10 gunicorn --workers 1 --bind 127.0.0.1:8002 --timeout 10 --log-level debug config.wsgi:application 2>&1 | head -100 || echo "  ⚠️  Gunicorn test tugadi"

# 7. Service file tekshirish
echo ""
echo "  → Service file tekshirish..."
cat /etc/systemd/system/phoenix-backend.service | head -30

# 8. Service logs (oxirgi 50 qator)
echo ""
echo "  → Service logs (oxirgi 50 qator)..."
sudo journalctl -u phoenix-backend --no-pager -n 50 | tail -40

# 9. Gunicorn error log
echo ""
echo "  → Gunicorn error log (agar mavjud bo'lsa)..."
if [ -f logs/gunicorn-error.log ]; then
    tail -50 logs/gunicorn-error.log
else
    echo "  ⚠️  Gunicorn error log topilmadi"
fi

deactivate

echo ""
echo "✅ Debug yakunlandi!"
