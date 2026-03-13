#!/bin/bash
# Phoenix to'liq deploy: backend + frontend + restart (ilmiyfaoliyat.uz)
# Ishga tushirish: bash deploy_phonix.sh  yoki  wget -qO- https://raw.githubusercontent.com/aiziyrak-coder/phonixB/master/deploy_phonix.sh | bash
set -e
DEPLOY_DIR="/phonix"
SERVICE_BACKEND="phoenix-backend"
export VITE_API_BASE_URL="${VITE_API_BASE_URL:-https://api.ilmiyfaoliyat.uz/api/v1}"
export VITE_MEDIA_URL="${VITE_MEDIA_URL:-https://api.ilmiyfaoliyat.uz/media/}"

echo "[1/6] Backend: git pull..."
cd "${DEPLOY_DIR}/backend"
git pull origin master || git pull origin main

echo "[2/6] Backend: migrate..."
source venv/bin/activate
pip install -r requirements.txt gunicorn -q
python manage.py migrate --noinput
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

echo "[5/6] Frontend: yangi build tayyor (static fayllar yangilandi)."
echo "[6/6] Nginx: reload (frontend sayt yangilanishi)..."
sudo systemctl reload nginx 2>/dev/null || true

echo ""
echo "=== TUGADI ==="
echo "Backend:  $(sudo systemctl is-active ${SERVICE_BACKEND} 2>/dev/null || echo '?')"
echo "Frontend: static build + nginx reload bajarildi."
