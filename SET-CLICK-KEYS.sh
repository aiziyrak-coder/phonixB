#!/bin/bash
# Click Service Secret Keys O'rnatish Scripti
# Ikkala service uchun ham kalitlarni avtomatik qo'shadi

echo "=========================================="
echo "   CLICK SERVICE SECRET KEYS"
echo "=========================================="
echo ""

# Backend papkasiga o'tish
cd /phonix/backend

# .env faylini tekshirish
if [ ! -f ".env" ]; then
    echo "❌ .env fayli topilmadi!"
    exit 1
fi

# Mavjud service key'larni o'chirish
echo "Mavjud service key'larni yangilash..."
sed -i '/CLICK_SERVICE_82154_SECRET_KEY/d' .env
sed -i '/CLICK_SERVICE_82154_MERCHANT_USER_ID/d' .env
sed -i '/CLICK_SERVICE_82155_SECRET_KEY/d' .env
sed -i '/CLICK_SERVICE_82155_MERCHANT_USER_ID/d' .env

# Click'dan berilgan kalitlarni qo'shish
cat >> .env << 'EOF'

# Click Service-specific secret keys (Click'dan berilgan kalitlar)
# Service 82154 uchun (Ilmiyfaoliyat.uz)
CLICK_SERVICE_82154_SECRET_KEY=XZC6u3JBBh
CLICK_SERVICE_82154_MERCHANT_USER_ID=63536
# Service 82155 uchun (Phoenix publication)
CLICK_SERVICE_82155_SECRET_KEY=icHbYQnMBx
CLICK_SERVICE_82155_MERCHANT_USER_ID=64985
EOF

echo "✅ Service secret key'lar .env fayliga qo'shildi!"
echo ""

# Tekshirish
echo "Tekshirish:"
grep "CLICK_SERVICE_82154_SECRET_KEY" .env
grep "CLICK_SERVICE_82155_SECRET_KEY" .env
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
echo "Ikkala service uchun ham kalitlar qo'shildi:"
echo "  ✅ Service 82154 (Ilmiyfaoliyat.uz): XZC6u3JBBh"
echo "  ✅ Service 82155 (Phoenix publication): icHbYQnMBx"
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
