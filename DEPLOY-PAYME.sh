#!/bin/bash
# Payme To'lov Tizimi - Server'da Deploy Script
# Bu scriptni server'da ishga tushiring

echo "=========================================="
echo "   PAYME TO'LOV TIZIMI - DEPLOY"
echo "=========================================="
echo ""

# 1. Backend'ni yangilash
echo "📦 1. Backend'ni Git'dan yangilash..."
cd /phonix/backend
git pull origin master

if [ $? -ne 0 ]; then
    echo "❌ Git pull xatolik! Qaytadan urinib ko'ring."
    exit 1
fi
echo "✅ Backend yangilandi"
echo ""

# 2. .env faylini tekshirish
echo "📋 2. Payme credentials tekshirish..."
if grep -q "PAYME_MERCHANT_ID=YOUR_MERCHANT_ID" .env; then
    echo "⚠️  PAYME_MERCHANT_ID hali to'ldirilmagan!"
    echo ""
    echo "Iltimos, .env faylini tahrirlang:"
    echo "  nano /phonix/backend/.env"
    echo ""
    echo "Quyidagi qatorlarni to'ldiring:"
    echo "  PAYME_MERCHANT_ID=sizning_merchant_id"
    echo "  PAYME_MERCHANT_KEY=sizning_merchant_key"
    echo "  PAYME_TEST_KEY=sizning_test_key"
    echo ""
    read -p "Credentials kiritdingizmi? (y/n): " response
    if [ "$response" != "y" ]; then
        echo "❌ Deploy bekor qilindi. Avval credentials kiriting."
        exit 1
    fi
fi
echo "✅ Credentials mavjud"
echo ""

# 3. Virtual environment aktivlashtirish
echo "🐍 3. Virtual environment..."
source venv/bin/activate

# 4. Migration qilish
echo "🗄️  4. Database migration..."
python manage.py makemigrations
python manage.py migrate

if [ $? -ne 0 ]; then
    echo "❌ Migration xatolik!"
    deactivate
    exit 1
fi
echo "✅ Migration muvaffaqiyatli"
echo ""

# 5. Payme service test
echo "🧪 5. Payme service test..."
python << 'EOF'
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/phonix/backend')
django.setup()

from apps.payments.payme_service import PaymeService

service = PaymeService()
print("=" * 60)
print(f"Merchant ID: {service.merchant_id}")
print(f"Is Test: {service.is_test}")
print(f"Endpoint: {service.endpoint}")

if service.merchant_id == 'YOUR_MERCHANT_ID' or not service.merchant_id:
    print("\n❌ XATO: Payme credentials to'ldirilmagan!")
    print("Iltimos .env faylini tahrirlang")
    sys.exit(1)
else:
    print("\n✅ Payme service tayyor!")
print("=" * 60)
EOF

if [ $? -ne 0 ]; then
    echo "❌ Payme service xatolik!"
    deactivate
    exit 1
fi
echo ""

deactivate

# 6. Backend restart
echo "🔄 6. Backend'ni restart qilish..."
sudo systemctl restart phoenix-backend

sleep 3

sudo systemctl status phoenix-backend --no-pager | head -10

if sudo systemctl is-active --quiet phoenix-backend; then
    echo "✅ Backend muvaffaqiyatli restart qilindi"
else
    echo "❌ Backend restart xatolik!"
    echo "Log'larni tekshiring: sudo journalctl -u phoenix-backend -n 50"
    exit 1
fi
echo ""

# 7. Frontend yangilash
echo "📦 7. Frontend'ni yangilash..."
cd /phonix/frontend
git pull origin master

if [ $? -ne 0 ]; then
    echo "❌ Frontend git pull xatolik!"
    exit 1
fi
echo "✅ Frontend yangilandi"
echo ""

# 8. Frontend build (agar kerak bo'lsa)
if [ -f "package.json" ]; then
    echo "🔨 8. Frontend build..."
    npm run build
    
    if [ $? -ne 0 ]; then
        echo "⚠️  Frontend build xatolik, lekin davom ettiriladi..."
    else
        echo "✅ Frontend build muvaffaqiyatli"
    fi
else
    echo "⚠️  package.json topilmadi, build o'tkazib yuborildi"
fi
echo ""

# 9. Test
echo "🧪 9. To'lovni test qilish..."
echo ""
echo "Test uchun quyidagi buyruqni bajaring:"
echo ""
echo "  curl -X POST https://api.ilmiyfaoliyat.uz/api/v1/payments/payme/ \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"jsonrpc\":\"2.0\",\"method\":\"CheckPerformTransaction\",\"params\":{\"account\":{\"transaction_id\":\"test\"},\"amount\":100000},\"id\":1}'"
echo ""

# 10. Xulosa
echo "=========================================="
echo "   DEPLOY TUGALLANDI!"
echo "=========================================="
echo ""
echo "✅ Backend yangilandi va restart qilindi"
echo "✅ Frontend yangilandi"
echo "✅ Migration qo'llandi"
echo "✅ Payme service tayyor"
echo ""
echo "📋 KEYINGI QADAMLAR:"
echo ""
echo "1. Payme merchant account yarating: https://business.payme.uz"
echo "2. Payme merchant panel'da endpoint URL kiriting:"
echo "     https://api.ilmiyfaoliyat.uz/api/v1/payments/payme/"
echo "3. Frontend'da to'lov qiling (provider='payme')"
echo ""
echo "📊 Log'larni kuzatish:"
echo "  sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep payme"
echo ""
echo "🎉 MUVAFFAQIYAT!"
echo "=========================================="
