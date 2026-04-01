#!/bin/bash
# Phoenix to'liq deploy: backend + frontend + restart (ilmiyfaoliyat.uz)
# Boshqa loyihalarga ta'sir: faqat systemctl restart phoenix-backend va nginx reload.
# Boshqa servislar (medora, fjsti.ziyrak.org va hokazo) systemd orqali alohida — bu skript ularni to'xtatmaydi.
# Ishga tushirish: bash deploy_phonix.sh  yoki  wget -qO- https://raw.githubusercontent.com/aiziyrak-coder/phonixB/master/deploy_phonix.sh | bash
set -e
DEPLOY_DIR="/phonix"
SERVICE_BACKEND="phoenix-backend"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://api.ilmiyfaoliyat.uz/api/v1}"
export VITE_MEDIA_URL="${VITE_MEDIA_URL:-https://api.ilmiyfaoliyat.uz/media/}"

echo "[1/6] Backend: git pull..."
cd "${DEPLOY_DIR}/backend"
git pull origin master || git pull origin main

echo "[2/6] Backend: migrate va narxlar..."
source venv/bin/activate
pip install -r requirements.txt gunicorn -q
python manage.py migrate --noinput
python manage.py seed_service_prices 2>/dev/null || true
python manage.py collectstatic --noinput 2>/dev/null || true
deactivate

echo "[3/6] Frontend: git pull va build..."
cd "${DEPLOY_DIR}/frontend"
git fetch origin
git reset --hard origin/master
npm install --silent
npm run build

echo "[4/6] Backend: restart..."
sudo systemctl restart "${SERVICE_BACKEND}"

# Gunicorn tinglashni kutamiz (boshqa dasturlar portni band qilgan bo'lsa — 502 + "CORS" xato ko'rinadi)
sleep 3
HTTP_CODE=$(curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 2 --max-time 15 "http://127.0.0.1:8000/api/v1/auth/login/" || echo "000")
if [ "$HTTP_CODE" = "000" ]; then
  echo "[XATO] 127.0.0.1:8000 ga ulanib bo'lmadi (gunicorn ishlamayapti yoki boshqa port)."
  echo "        Tekshiring: sudo systemctl status ${SERVICE_BACKEND} --no-pager | head -25"
  echo "        Log: sudo journalctl -u ${SERVICE_BACKEND} -n 40 --no-pager"
  exit 1
fi
# GET login odatda 405 — bu normal (endpoint POST). 200/400/401 ham bo'lishi mumkin.
case "$HTTP_CODE" in
  405|200|400|401|403) ;;
  *)
    echo "[OGohlantirish] Loopback javob HTTP $HTTP_CODE (kutilgan: 405 yoki 4xx/200)."
    ;;
esac

echo "[5/6] Frontend: yangi build tayyor (static fayllar yangilandi)."
echo "[5b/6] Nginx api: eski 8003 -> 8000 (faqat api-ilmiyfaoliyat.conf)..."
API_NGX="/etc/nginx/sites-available/api-ilmiyfaoliyat.conf"
if [ -f "$API_NGX" ] && grep -q '127.0.0.1:8003' "$API_NGX" 2>/dev/null; then
  sudo sed -i 's/127.0.0.1:8003/127.0.0.1:8000/g' "$API_NGX"
  echo "      proxy_pass 8003 -> 8000 tuzatildi."
fi
echo "[6/6] Nginx: reload (frontend sayt yangilanishi)..."
sudo nginx -t 2>/dev/null && sudo systemctl reload nginx 2>/dev/null || true

echo ""
echo "=== TUGADI ==="
echo "Backend:  $(sudo systemctl is-active ${SERVICE_BACKEND} 2>/dev/null || echo '?')"
echo "Loopback: HTTP ${HTTP_CODE} (login endpoint)"
echo "Frontend: static build + nginx reload bajarildi."
