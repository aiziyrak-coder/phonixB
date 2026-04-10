#!/bin/bash
# Click service kalitlarini .env ga yozish (kalitlar repoda SAQLANMAYDI).
#
# Ishlatish (serverda):
#   export CLICK_SERVICE_82154_SECRET_KEY='...'
#   export CLICK_SERVICE_82155_SECRET_KEY='...'
#   export CLICK_SERVICE_82154_MERCHANT_USER_ID='63536'   # ixtiyoriy
#   export CLICK_SERVICE_82155_MERCHANT_USER_ID='64985'   # ixtiyoriy
#   bash SET-CLICK-KEYS.sh

set -euo pipefail

: "${CLICK_SERVICE_82154_SECRET_KEY:?82154 secret kerak (export qiling)}"
: "${CLICK_SERVICE_82155_SECRET_KEY:?82155 secret kerak (export qiling)}"

M54="${CLICK_SERVICE_82154_MERCHANT_USER_ID:-63536}"
M55="${CLICK_SERVICE_82155_MERCHANT_USER_ID:-64985}"

cd /phonix/backend

if [ ! -f ".env" ]; then
    echo ".env topilmadi"
    exit 1
fi

echo "Mavjud service key qatorlari yangilanmoqda..."
sed -i '/CLICK_SERVICE_82154_SECRET_KEY/d' .env
sed -i '/CLICK_SERVICE_82154_MERCHANT_USER_ID/d' .env
sed -i '/CLICK_SERVICE_82155_SECRET_KEY/d' .env
sed -i '/CLICK_SERVICE_82155_MERCHANT_USER_ID/d' .env

cat >> .env << EOF

# Click service kalitlari (SET-CLICK-KEYS.sh orqali)
CLICK_SERVICE_82154_SECRET_KEY=${CLICK_SERVICE_82154_SECRET_KEY}
CLICK_SERVICE_82154_MERCHANT_USER_ID=${M54}
CLICK_SERVICE_82155_SECRET_KEY=${CLICK_SERVICE_82155_SECRET_KEY}
CLICK_SERVICE_82155_MERCHANT_USER_ID=${M55}
EOF

echo "Tekshirish (qiymatlar chiqarilmaydi):"
grep -q '^CLICK_SERVICE_82154_SECRET_KEY=' .env && echo "  82154: OK"
grep -q '^CLICK_SERVICE_82155_SECRET_KEY=' .env && echo "  82155: OK"

sudo systemctl restart phoenix-backend
sleep 2
sudo systemctl is-active phoenix-backend && echo "phoenix-backend: active"
