#!/bin/bash
# CORS Fix Script for Server
# Bu script server'da CORS muammosini tuzatish uchun

set -e

echo "🔧 CORS muammosini tuzatish..."

# 1. Backend .env faylini yangilash
cd /phonix/backend

echo "  → .env faylini yangilash..."
if [ ! -f .env ]; then
    echo "⚠️  .env fayl topilmadi, yaratilmoqda..."
    touch .env
fi

# CORS sozlamalarini qo'shish/yangilash
if grep -q "CORS_ALLOWED_ORIGINS" .env; then
    # Mavjud sozlamani yangilash
    sed -i 's|^CORS_ALLOWED_ORIGINS=.*|CORS_ALLOWED_ORIGINS=https://ilmiyfaoliyat.uz,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173|' .env
    echo "  ✅ CORS_ALLOWED_ORIGINS yangilandi"
else
    # Yangi sozlama qo'shish
    echo "" >> .env
    echo "# CORS Settings" >> .env
    echo "CORS_ALLOW_ALL_ORIGINS=False" >> .env
    echo "CORS_ALLOWED_ORIGINS=https://ilmiyfaoliyat.uz,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173" >> .env
    echo "  ✅ CORS sozlamalari qo'shildi"
fi

# CORS_ALLOW_ALL_ORIGINS ni False qilish
if grep -q "CORS_ALLOW_ALL_ORIGINS" .env; then
    sed -i 's|^CORS_ALLOW_ALL_ORIGINS=.*|CORS_ALLOW_ALL_ORIGINS=False|' .env
else
    echo "CORS_ALLOW_ALL_ORIGINS=False" >> .env
fi

echo "  ✅ .env fayl yangilandi"

# 2. Backend service'ni restart qilish
echo "  → Backend service'ni restart qilish..."
sudo systemctl restart phoenix-backend
sleep 2

# 3. Service status tekshirish
echo "  → Service status tekshirish..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "  ✅ Backend service ishlayapti"
else
    echo "  ❌ Backend service ishlamayapti!"
    sudo systemctl status phoenix-backend --no-pager | head -10
    exit 1
fi

# 4. CORS test qilish
echo ""
echo "  → CORS test qilish..."
TEST_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -H "Origin: https://ilmiyfaoliyat.uz" \
    -H "Access-Control-Request-Method: POST" \
    -H "Access-Control-Request-Headers: content-type" \
    -X OPTIONS https://api.ilmiyfaoliyat.uz/api/v1/auth/login/)

if [ "$TEST_RESPONSE" = "200" ] || [ "$TEST_RESPONSE" = "204" ]; then
    echo "  ✅ CORS preflight test muvaffaqiyatli (HTTP $TEST_RESPONSE)"
else
    echo "  ⚠️  CORS preflight test javob: HTTP $TEST_RESPONSE"
fi

# 5. CORS header'larni tekshirish
echo ""
echo "  → CORS header'larni tekshirish..."
CORS_HEADER=$(curl -s -I -H "Origin: https://ilmiyfaoliyat.uz" \
    -X OPTIONS https://api.ilmiyfaoliyat.uz/api/v1/auth/login/ | grep -i "access-control-allow-origin" || echo "NOT_FOUND")

if echo "$CORS_HEADER" | grep -q "ilmiyfaoliyat.uz"; then
    echo "  ✅ CORS header to'g'ri: $CORS_HEADER"
else
    echo "  ⚠️  CORS header topilmadi yoki noto'g'ri: $CORS_HEADER"
fi

echo ""
echo "✅ CORS tuzatish jarayoni yakunlandi!"
echo ""
echo "📝 Keyingi qadamlar:"
echo "  1. Browser'da cache'ni tozalang (Ctrl+Shift+Delete)"
echo "  2. Saytni qayta yuklang"
echo "  3. Agar muammo davom etsa, browser console'da xatoliklarni tekshiring"
echo ""
echo "🔍 Logs ko'rish:"
echo "  sudo journalctl -u phoenix-backend -f --lines=50"
