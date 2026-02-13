#!/bin/bash
# Click Service 82154 Secret Key O'rnatish Scripti
# Bu script .env fayliga secret key qo'shadi

echo "=========================================="
echo "   CLICK SERVICE 82154 SECRET KEY"
echo "=========================================="
echo ""

# Ma'lumotlarni so'rash
read -p "Click'dan olgan Service 82154 secret key'ni kiriting: " SECRET_KEY

if [ -z "$SECRET_KEY" ]; then
    echo "❌ Secret key kiritilmadi!"
    exit 1
fi

echo ""
echo "Secret key qabul qilindi: ${SECRET_KEY:0:10}..."
echo ""

# Backend papkasiga o'tish
cd /phonix/backend

# .env faylini tekshirish
if [ ! -f ".env" ]; then
    echo "❌ .env fayli topilmadi!"
    exit 1
fi

# Mavjud CLICK_SERVICE_82154_SECRET_KEY ni tekshirish va o'chirish
if grep -q "CLICK_SERVICE_82154_SECRET_KEY" .env; then
    echo "⚠️  Mavjud secret key topildi, yangilanmoqda..."
    sed -i '/CLICK_SERVICE_82154_SECRET_KEY/d' .env
fi

# Yangi secret key qo'shish
cat >> .env << EOF

# Click Service 82154 secret key (Set on $(date))
CLICK_SERVICE_82154_SECRET_KEY=$SECRET_KEY
EOF

echo "✅ Secret key .env fayliga qo'shildi!"
echo ""

# Tekshirish
echo "Tekshirish:"
grep "CLICK_SERVICE_82154_SECRET_KEY" .env
echo ""

# Backend restart
echo "Backend'ni restart qilish..."
sudo systemctl restart phoenix-backend
sleep 2

if sudo systemctl is-active --quiet phoenix-backend; then
    echo "✅ Backend muvaffaqiyatli restart qilindi"
else
    echo "❌ Backend restart xatolik!"
    sudo journalctl -u phoenix-backend -n 20 --no-pager
    exit 1
fi

echo ""
echo "=========================================="
echo "   ✅ TAYYOR!"
echo "=========================================="
echo ""
echo "Endi Click'dan kelgan prepare callback'lar ishlashi kerak!"
echo ""
echo "Test qilish:"
echo "  1. Frontend'da to'lov yarating"
echo "  2. Click sahifasiga o'ting"
echo "  3. To'lovni amalga oshiring"
echo "  4. Log'larni kuzating:"
echo "     sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep signature"
echo ""
