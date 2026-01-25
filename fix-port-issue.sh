#!/bin/bash
# Port 8000 muammosini tuzatish
# Bu script port 8000'ni ishlatayotgan process'larni topib o'chiradi

set -e

echo "🔧 Port 8000 muammosini tuzatish..."
echo ""

# 1. Service'ni to'xtatish
echo "  → Backend service'ni to'xtatish..."
sudo systemctl stop phoenix-backend
sleep 2

# 2. Port 8000'ni ishlatayotgan process'larni topish va o'chirish
echo "  → Port 8000'ni ishlatayotgan process'larni topish..."
PORT_PIDS=$(sudo lsof -ti:8000 2>/dev/null || echo "")

if [ -n "$PORT_PIDS" ]; then
    echo "  ⚠️  Port 8000'ni ishlatayotgan process'lar topildi: $PORT_PIDS"
    echo "  → Process'larni o'chirish..."
    echo "$PORT_PIDS" | xargs -r sudo kill -9 2>/dev/null || true
    sleep 2
    echo "  ✅ Process'lar o'chirildi"
else
    echo "  ✅ Port 8000 bo'sh"
fi

# 3. Barcha gunicorn process'larni o'chirish
echo "  → Barcha gunicorn process'larni o'chirish..."
GUNICORN_PIDS=$(pgrep -f gunicorn || echo "")
if [ -n "$GUNICORN_PIDS" ]; then
    echo "  ⚠️  Gunicorn process'lar topildi: $GUNICORN_PIDS"
    echo "$GUNICORN_PIDS" | xargs -r sudo kill -9 2>/dev/null || true
    sleep 2
    echo "  ✅ Gunicorn process'lar o'chirildi"
else
    echo "  ✅ Gunicorn process'lar yo'q"
fi

# 4. Port'ni qayta tekshirish
echo "  → Port 8000'ni qayta tekshirish..."
if sudo lsof -ti:8000 >/dev/null 2>&1; then
    echo "  ⚠️  Port 8000 hali ham band!"
    echo "  → Qo'shimcha process'larni o'chirish..."
    sudo fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
else
    echo "  ✅ Port 8000 bo'sh"
fi

# 5. Service'ni qayta ishga tushirish
echo ""
echo "  → Backend service'ni qayta ishga tushirish..."
sudo systemctl start phoenix-backend
sleep 3

# 6. Service status tekshirish
echo ""
echo "  → Service status tekshirish..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✅ Backend service muvaffaqiyatli ishga tushdi!"
    sudo systemctl status phoenix-backend --no-pager | head -10
else
    echo "  ❌ Backend service ishga tushmadi!"
    echo ""
    echo "  → Xatoliklar:"
    sudo journalctl -u phoenix-backend --no-pager -n 20 | tail -15
    exit 1
fi

# 7. Port tekshirish
echo ""
echo "  → Port 8000 tekshirish..."
if sudo lsof -ti:8000 >/dev/null 2>&1; then
    PORT_PID=$(sudo lsof -ti:8000)
    echo "  ✅ Port 8000 ishlatilmoqda (PID: $PORT_PID)"
else
    echo "  ⚠️  Port 8000 hali ham bo'sh - service ishlamayapti"
fi

echo ""
echo "✅ Port muammosi tuzatildi!"
