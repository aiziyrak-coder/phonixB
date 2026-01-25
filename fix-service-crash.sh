#!/bin/bash
# Service Crash Muammosini Tuzatish
# Bu script service'ning crash qilish muammosini hal qiladi

set -e

echo "🔧 Service crash muammosini tuzatish..."
echo ""

cd /phonix/backend

# 1. Service'ni to'xtatish
echo "  → Service'ni to'xtatish..."
sudo systemctl stop phoenix-backend
sleep 3

# 2. Port 8000'ni to'liq bo'shatish
echo "  → Port 8000'ni to'liq bo'shatish..."
# Barcha port 8000'ni ishlatayotgan process'larni o'chirish
PORT_PIDS=$(sudo lsof -ti:8000 2>/dev/null || echo "")
if [ -n "$PORT_PIDS" ]; then
    echo "  ⚠️  Port 8000'ni ishlatayotgan process'lar: $PORT_PIDS"
    for PID in $PORT_PIDS; do
        if ps -p $PID >/dev/null 2>&1; then
            echo "  → Process $PID ni o'chirish..."
            sudo kill -9 $PID 2>/dev/null || true
        fi
    done
    sleep 2
fi

# 3. Barcha gunicorn process'larni o'chirish (faqat phoenix-backend'ga tegishli)
echo "  → Phoenix backend gunicorn process'larni o'chirish..."
GUNICORN_PIDS=$(pgrep -f "gunicorn.*phonix.*backend" || pgrep -f "gunicorn.*config.wsgi" | xargs -I {} sh -c 'ps -p {} -o cmd= | grep -q "/phonix/backend" && echo {}' || echo "")
if [ -n "$GUNICORN_PIDS" ]; then
    echo "  ⚠️  Gunicorn process'lar: $GUNICORN_PIDS"
    for PID in $GUNICORN_PIDS; do
        if ps -p $PID >/dev/null 2>&1; then
            echo "  → Process $PID ni o'chirish..."
            sudo kill -9 $PID 2>/dev/null || true
        fi
    done
    sleep 2
fi

# 4. Port'ni qayta tekshirish
echo "  → Port 8000'ni qayta tekshirish..."
if sudo lsof -ti:8000 >/dev/null 2>&1; then
    echo "  ⚠️  Port 8000 hali ham band!"
    sudo fuser -k 8000/tcp 2>/dev/null || true
    sleep 2
else
    echo "  ✅ Port 8000 bo'sh"
fi

# 5. Logs papkasini tekshirish
echo "  → Logs papkasini tekshirish..."
if [ ! -d logs ]; then
    mkdir -p logs
    chmod 755 logs
    echo "  ✅ Logs papkasi yaratildi"
fi

# 6. Service'ni qayta ishga tushirish
echo ""
echo "  → Service'ni qayta ishga tushirish..."
sudo systemctl start phoenix-backend
sleep 5  # Kattaroq kutish

# 7. Service status tekshirish
echo ""
echo "  → Service status tekshirish..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✅ Backend service muvaffaqiyatli ishga tushdi!"
    sudo systemctl status phoenix-backend --no-pager | head -15
else
    echo "  ❌ Backend service ishga tushmadi!"
    echo ""
    echo "  → Xatoliklar:"
    sudo journalctl -u phoenix-backend --no-pager -n 30 | tail -20
    
    # Gunicorn error log
    if [ -f logs/gunicorn-error.log ]; then
        echo ""
        echo "  → Gunicorn error log (oxirgi 20 qator):"
        tail -20 logs/gunicorn-error.log
    fi
    
    exit 1
fi

# 8. Port tekshirish
echo ""
echo "  → Port 8000 tekshirish..."
if sudo lsof -ti:8000 >/dev/null 2>&1; then
    PORT_PID=$(sudo lsof -ti:8000)
    echo "  ✅ Port 8000 ishlatilmoqda (PID: $PORT_PID)"
else
    echo "  ⚠️  Port 8000 hali ham bo'sh - service ishlamayapti"
fi

echo ""
echo "✅ Service crash muammosi tuzatildi!"
