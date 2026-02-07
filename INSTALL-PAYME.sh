#!/bin/bash
# PAYME TO'LOV TIZIMI - AVTOMATIK O'RNATISH
# Bitta buyruq bilan hammasi!

set -e  # Xatolik bo'lsa to'xtaydi

echo "=========================================="
echo "   PAYME - AVTOMATIK O'RNATISH"
echo "=========================================="
echo ""

# Ranglar
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ma'lumotlarni so'rash
echo -e "${BLUE}📋 PAYME CREDENTIALS KIRITING:${NC}"
echo ""
read -p "Payme Merchant ID: " MERCHANT_ID
read -p "Payme Production Key: " PROD_KEY
read -p "Payme Test Key: " TEST_KEY
read -p "Test rejimda ishlatilsinmi? (y/n, default: y): " IS_TEST

# Default qiymat
if [ -z "$IS_TEST" ] || [ "$IS_TEST" = "y" ]; then
    IS_TEST_VALUE="True"
else
    IS_TEST_VALUE="False"
fi

echo ""
echo -e "${GREEN}✅ Ma'lumotlar qabul qilindi${NC}"
echo ""

# ============================================
# 1. BACKEND YANGILASH
# ============================================
echo -e "${BLUE}📦 1/6 Backend'ni Git'dan yangilash...${NC}"
cd /phonix/backend
git pull origin master

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Git pull xatolik!${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Backend yangilandi${NC}"
echo ""

# ============================================
# 2. .ENV FAYLINI AVTOMATIK YANGILASH
# ============================================
echo -e "${BLUE}📝 2/6 .env faylini yangilash...${NC}"

# Payme qatorlari mavjudmi tekshirish
if grep -q "PAYME_MERCHANT_ID" .env; then
    echo -e "${YELLOW}⚠️  Payme credentials mavjud, yangilanmoqda...${NC}"
    
    # Mavjud qatorlarni o'chirish
    sed -i '/PAYME_MERCHANT_ID/d' .env
    sed -i '/PAYME_MERCHANT_KEY/d' .env
    sed -i '/PAYME_TEST_KEY/d' .env
    sed -i '/PAYME_IS_TEST/d' .env
    sed -i '/PAYME_ENDPOINT/d' .env
fi

# Yangi qatorlarni qo'shish
cat >> .env << EOF

# Payme Payment (Auto-configured on $(date))
PAYME_MERCHANT_ID=$MERCHANT_ID
PAYME_MERCHANT_KEY=$PROD_KEY
PAYME_TEST_KEY=$TEST_KEY
PAYME_IS_TEST=$IS_TEST_VALUE
PAYME_ENDPOINT=https://checkout.paycom.uz
EOF

echo -e "${GREEN}✅ .env fayli yangilandi${NC}"
echo ""

# ============================================
# 3. MIGRATION
# ============================================
echo -e "${BLUE}🗄️  3/6 Database migration...${NC}"
source venv/bin/activate

python manage.py makemigrations
python manage.py migrate

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Migration xatolik!${NC}"
    deactivate
    exit 1
fi

echo -e "${GREEN}✅ Migration muvaffaqiyatli${NC}"
echo ""

# ============================================
# 4. PAYME SERVICE TEST
# ============================================
echo -e "${BLUE}🧪 4/6 Payme service test...${NC}"

python << EOF
import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/phonix/backend')
django.setup()

from apps.payments.payme_service import PaymeService

service = PaymeService()
print("=" * 60)
print(f"Merchant ID: {service.merchant_id}")
print(f"Test Mode: {service.is_test}")
print(f"Endpoint: {service.endpoint}")

if not service.merchant_id or service.merchant_id == 'YOUR_MERCHANT_ID':
    print("\n❌ XATO: Credentials noto'g'ri!")
    sys.exit(1)
else:
    print("\n✅ Payme service tayyor!")
print("=" * 60)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Payme service test xatolik!${NC}"
    deactivate
    exit 1
fi

deactivate
echo -e "${GREEN}✅ Payme service ishlayapti${NC}"
echo ""

# ============================================
# 5. BACKEND RESTART
# ============================================
echo -e "${BLUE}🔄 5/6 Backend restart...${NC}"
sudo systemctl restart phoenix-backend
sleep 3

if sudo systemctl is-active --quiet phoenix-backend; then
    echo -e "${GREEN}✅ Backend muvaffaqiyatli restart qilindi${NC}"
else
    echo -e "${RED}❌ Backend restart xatolik!${NC}"
    sudo journalctl -u phoenix-backend -n 20 --no-pager
    exit 1
fi
echo ""

# ============================================
# 6. FRONTEND YANGILASH
# ============================================
echo -e "${BLUE}📦 6/6 Frontend yangilash...${NC}"
cd /phonix/frontend
git pull origin master

if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Frontend git pull xatolik, lekin davom etamiz...${NC}"
fi

# Frontend build (agar package.json mavjud bo'lsa)
if [ -f "package.json" ]; then
    echo -e "${BLUE}🔨 Frontend build...${NC}"
    npm run build 2>/dev/null || echo -e "${YELLOW}⚠️  Build xatolik, lekin davom etamiz${NC}"
fi

echo -e "${GREEN}✅ Frontend yangilandi${NC}"
echo ""

# ============================================
# XULOSA
# ============================================
echo ""
echo "=========================================="
echo -e "${GREEN}   ✅ O'RNATISH TUGALLANDI!${NC}"
echo "=========================================="
echo ""
echo -e "${GREEN}Backend:${NC} ✅ Yangilandi va ishga tushdi"
echo -e "${GREEN}Frontend:${NC} ✅ Yangilandi"
echo -e "${GREEN}Database:${NC} ✅ Migration qo'llandi"
echo -e "${GREEN}Payme:${NC} ✅ Sozlandi"
echo ""
echo "=========================================="
echo -e "${BLUE}📋 KEYINGI QADAM:${NC}"
echo "=========================================="
echo ""
echo "Payme Merchant Panel'ga kiring:"
echo "  🌐 https://business.payme.uz"
echo ""
echo "Endpoint URL kiriting:"
echo "  📍 https://api.ilmiyfaoliyat.uz/api/v1/payments/payme/"
echo "  📍 Method: POST"
echo "  📍 Protocol: JSON-RPC 2.0"
echo ""
echo "=========================================="
echo -e "${BLUE}🧪 TEST QILISH:${NC}"
echo "=========================================="
echo ""
echo "Backend test:"
echo "  cd /phonix/backend"
echo "  source venv/bin/activate"
echo "  python -c 'from apps.payments.payme_service import PaymeService; s=PaymeService(); print(f\"Merchant: {s.merchant_id}\")'"
echo ""
echo "Frontend'da:"
echo "  🌐 https://ilmiyfaoliyat.uz"
echo "  💳 Provider: Payme tanlang"
echo "  💰 To'lov qiling"
echo ""
echo "=========================================="
echo -e "${BLUE}📊 LOG'LARNI KUZATISH:${NC}"
echo "=========================================="
echo ""
echo "  sudo tail -f /phonix/backend/logs/gunicorn-error.log | grep payme"
echo ""
echo "=========================================="
echo -e "${GREEN}🎉 MUVAFFAQIYAT!${NC}"
echo "=========================================="
echo ""
echo -e "${YELLOW}Eslatma: Payme merchant panel'da endpoint URL kiritishni${NC}"
echo -e "${YELLOW}unutmang (business.payme.uz)${NC}"
echo ""
