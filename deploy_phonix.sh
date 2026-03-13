#!/bin/bash
# Phoenix to'liq deploy: backend + frontend + restart (ilmiyfaoliyat.uz)
# Ishga tushirish: bash deploy_phonix.sh  yoki  wget -qO- https://raw.githubusercontent.com/aiziyrak-coder/phonixB/master/deploy_phonix.sh | bash
set -e
DEPLOY_DIR="/phonix"
SERVICE_BACKEND="phoenix-backend"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://api.ilmiyfaoliyat.uz/api/v1}"
export VITE_MEDIA_URL="${VITE_MEDIA_URL:-https://api.ilmiyfaoliyat.uz/media/}"

echo "[1/5] Backend: pull..."
cd "${DEPLOY_DIR}/backend"
git pull origin master || git pull origin main

echo "[2/5] Backend: migrate..."
source venv/bin/activate
pip install -r requirements.txt gunicorn -q
python manage.py migrate --noinput
python manage.py collectstatic --noinput 2>/dev/null || true
deactivate

echo "[3/5] Frontend: fetch va build..."
cd "${DEPLOY_DIR}/frontend"
git fetch origin
git reset --hard origin/master
npm install --silent
npm run build

echo "[4/5] Backend restart..."
sudo systemctl restart "${SERVICE_BACKEND}"

echo "[5/5] Nginx reload (static yangilanishi uchun)..."
sudo systemctl reload nginx 2>/dev/null || true

echo "[OK] Deploy tugadi. Backend status:"
sudo systemctl is-active "${SERVICE_BACKEND}" && echo "phoenix-backend: ishlayapti" || echo "phoenix-backend: xato"
