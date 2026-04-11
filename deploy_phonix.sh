#!/bin/bash

# Phoenix Scientific Platform - Xavfsiz Deployment Script
# Bu script faqat Phoenix dasturini yangilaydi va boshqa dasturlarga tasir qilmaydi
# GitHub: https://github.com/aiziyrak-coder/phonixB
#
# MUHIM: Nginx konfiglarini avtomatik sed qilmaymiz — boshqa saytlar buzilishining oldini oladi.
#        API proxy port: PHONIX_BACKEND_PORT (default 8050) — systemd va nginx bilan moslang.

set -e  # Xatolik bo'lsa to'xtatish

# ============================================
# KONFIGURATSIYA - Faqat Phoenix uchun
# ============================================
DEPLOY_DIR="/phonix"
BACKEND_REPO="https://github.com/aiziyrak-coder/phonixB.git"
FRONTEND_REPO="https://github.com/aiziyrak-coder/phonixF.git"
SERVICE_NAME="phoenix-backend"
# Loopback port — 8000 boshqa xizmatlar bilan to'qnashmasin; PHONIX_BACKEND_PORT bilan o'zgartirish mumkin
BACKEND_PORT="${PHONIX_BACKEND_PORT:-8050}"
FRONTEND_DOMAIN="ilmiyfaoliyat.uz"
API_DOMAIN="api.ilmiyfaoliyat.uz"
# PHONIX_GIT_RESET=true — fetch + reset --hard (masofadan deploy uchun tavsiya)

# ============================================
# FUNKTSIYALAR
# ============================================

git_update_backend() {
    if [ "${PHONIX_GIT_RESET:-false}" = "true" ]; then
        echo "   Git fetch + reset --hard (PHONIX_GIT_RESET)..."
        cp -a .env /tmp/.env.phonix.bak 2>/dev/null || true
        git fetch origin master 2>/dev/null || git fetch origin main
        git reset --hard origin/master 2>/dev/null || git reset --hard origin/main
        if [ -f /tmp/.env.phonix.bak ]; then
            cp -a /tmp/.env.phonix.bak .env
            echo "   .env tiklandi"
        fi
    else
        echo "   Git pull qilinmoqda..."
        git stash 2>/dev/null || true
        git pull origin master || git pull origin main || error_exit "Git pull xatolik"
        git stash pop 2>/dev/null || true
    fi
}

git_update_frontend() {
    if [ "${PHONIX_GIT_RESET:-false}" = "true" ]; then
        echo "   Git fetch + reset --hard (PHONIX_GIT_RESET)..."
        git fetch origin master 2>/dev/null || git fetch origin main
        git reset --hard origin/master 2>/dev/null || git reset --hard origin/main
    else
        echo "   Git pull qilinmoqda..."
        git stash 2>/dev/null || true
        git pull origin master || git pull origin main || error_exit "Git pull xatolik"
        git stash pop 2>/dev/null || true
    fi
}

# Xatolikni ko'rsatish
error_exit() {
    echo "❌ Xatolik: $1" >&2
    exit 1
}

# Tekshirish - boshqa service'lar ishlayaptimi?
check_other_services() {
    echo "🔍 Boshqa service'larni tekshirish..."
    
    # Phoenix service'ni tekshirish
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        echo "✅ ${SERVICE_NAME} ishlayapti"
    else
        echo "⚠️  ${SERVICE_NAME} ishlamayapti"
    fi
    
    # Port tekshirish
    if netstat -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
        echo "✅ Port ${BACKEND_PORT} ishlatilmoqda"
    else
        echo "⚠️  Port ${BACKEND_PORT} bo'sh"
    fi
}

# Backup yaratish
create_backup() {
    echo "💾 Backup yaratish..."
    
    BACKUP_DIR="${DEPLOY_DIR}/backups/$(date +%Y%m%d_%H%M%S)"
    mkdir -p ${BACKUP_DIR}
    
    # Backend backup
    if [ -d "${DEPLOY_DIR}/backend" ]; then
        echo "📦 Backend backup..."
        cp -r ${DEPLOY_DIR}/backend ${BACKUP_DIR}/backend 2>/dev/null || true
    fi
    
    # Frontend backup
    if [ -d "${DEPLOY_DIR}/frontend" ]; then
        echo "📦 Frontend backup..."
        cp -r ${DEPLOY_DIR}/frontend ${BACKUP_DIR}/frontend 2>/dev/null || true
    fi
    
    # .env backup
    if [ -f "${DEPLOY_DIR}/backend/.env" ]; then
        echo "📦 .env backup..."
        cp ${DEPLOY_DIR}/backend/.env ${BACKUP_DIR}/.env
    fi
    
    echo "✅ Backup yaratildi: ${BACKUP_DIR}"
}

# ============================================
# ASOSIY DEPLOYMENT
# ============================================

echo "🚀 Phoenix Deployment boshlandi..."
echo "📅 Vaqt: $(date)"
echo ""

# 1. Tekshirishlar
check_other_services
echo ""

# 2. Backup
create_backup
echo ""

# 3. Backend yangilash
echo "📦 Backend yangilanmoqda..."
cd ${DEPLOY_DIR}

if [ -d "backend/.git" ]; then
    cd backend
    git_update_backend
else
    echo "   Backend clone qilinmoqda..."
    cd ${DEPLOY_DIR}
    [ -d "backend" ] && rm -rf backend
    git clone ${BACKEND_REPO} backend || error_exit "Backend clone xatolik"
    cd backend
fi

# Virtual environment
if [ ! -d "venv" ]; then
    echo "   Virtual environment yaratilmoqda..."
    python3 -m venv venv
fi

echo "   Dependencies o'rnatilmoqda..."
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt gunicorn -q || error_exit "Dependencies o'rnatish xatolik"

# .env faylini saqlab qolish
if [ ! -f .env ] && [ -f "${BACKUP_DIR}/.env" ]; then
    echo "   .env fayli restore qilinmoqda..."
    cp ${BACKUP_DIR}/.env .env
fi

# Migrations
echo "   Migrations ishga tushirilmoqda..."
python manage.py migrate --noinput || error_exit "Migrations xatolik"

# Static files
echo "   Static files collect qilinmoqda..."
python manage.py collectstatic --noinput || error_exit "Collectstatic xatolik"

deactivate
echo "✅ Backend yangilandi"
echo ""

# 4. Frontend yangilash
echo "📦 Frontend yangilanmoqda..."
cd ${DEPLOY_DIR}

if [ -d "frontend/.git" ]; then
    cd frontend
    git_update_frontend
else
    echo "   Frontend clone qilinmoqda..."
    cd ${DEPLOY_DIR}
    [ -d "frontend" ] && rm -rf frontend
    git clone ${FRONTEND_REPO} frontend || error_exit "Frontend clone xatolik"
    cd frontend
fi

# Dependencies va build
echo "   Dependencies o'rnatilmoqda..."
npm install --silent || error_exit "npm install xatolik"

echo "   Frontend build qilinmoqda..."
export VITE_API_BASE_URL="https://${API_DOMAIN}/api/v1"
export VITE_MEDIA_URL="https://${API_DOMAIN}/media/"

npm run build || error_exit "Frontend build xatolik"

# Nginx static (ixtiyoriy): PHONIX_FRONTEND_WEB_ROOT=/var/www/ilmiyfaoliyat shaklida
if [ -n "${PHONIX_FRONTEND_WEB_ROOT:-}" ] && [ -d "dist" ]; then
    echo "   Static fayllar nginx papkasiga nusxalanmoqda: ${PHONIX_FRONTEND_WEB_ROOT}"
    mkdir -p "${PHONIX_FRONTEND_WEB_ROOT}"
    rsync -a --delete dist/ "${PHONIX_FRONTEND_WEB_ROOT}/" || error_exit "rsync static xatolik"
    if command -v nginx >/dev/null 2>&1; then
        sudo nginx -t 2>/dev/null && sudo systemctl reload nginx 2>/dev/null || true
    fi
fi

echo "✅ Frontend yangilandi"
echo ""

# 5. Service restart (Graceful)
echo "🔄 Service restart qilinmoqda..."

# Graceful restart - avval reload, agar ishlamasa restart
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "   Service reload qilinmoqda..."
    sudo systemctl reload ${SERVICE_NAME} 2>/dev/null || sudo systemctl restart ${SERVICE_NAME}
else
    echo "   Service start qilinmoqda..."
    sudo systemctl start ${SERVICE_NAME}
fi

# Service status
sleep 2
echo ""
echo "📊 Service status:"
sudo systemctl status ${SERVICE_NAME} --no-pager | head -15

# 6. Tekshirish
echo ""
echo "🔍 Tekshirishlar:"

# Service status
if systemctl is-active --quiet ${SERVICE_NAME}; then
    echo "✅ Service ishlayapti"
else
    echo "❌ Service ishlamayapti"
    error_exit "Service ishlamayapti"
fi

# Port tekshirish
if netstat -tlnp 2>/dev/null | grep -q ":${BACKEND_PORT} "; then
    echo "✅ Port ${BACKEND_PORT} ishlatilmoqda"
else
    echo "⚠️  Port ${BACKEND_PORT} bo'sh (service ishlamayotgan bo'lishi mumkin)"
fi

# API test
echo "   API test qilinmoqda..."
if curl -s -o /dev/null -w "%{http_code}" "https://${API_DOMAIN}/api/v1/" | grep -q "200\|404\|405"; then
    echo "✅ API javob berayapti"
else
    echo "⚠️  API javob bermayapti (Nginx yoki service muammosi bo'lishi mumkin)"
fi

# Health (loopback)
echo "   Health tekshiruvi (127.0.0.1:${BACKEND_PORT})..."
if curl -sf --max-time 5 "http://127.0.0.1:${BACKEND_PORT}/health/" >/dev/null; then
    echo "✅ /health/ OK"
else
    echo "⚠️  /health/ javob bermadi (port yoki gunicorn)"
fi
if code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://127.0.0.1:${BACKEND_PORT}/health/ready/"); then
    if [ "$code" = "200" ]; then
        echo "✅ /health/ready/ 200"
    else
        echo "⚠️  /health/ready/ HTTP $code (DB yoki Redis muammosi bo'lishi mumkin)"
    fi
else
    echo "⚠️  /health/ready/ so'rovi xato"
fi

# ============================================
# YAKUNIY XABAR
# ============================================

echo ""
echo "✅ Deployment muvaffaqiyatli yakunlandi!"
echo ""
echo "📝 Keyingi qadamlar:"
echo "   1. Logs tekshirish: sudo journalctl -u ${SERVICE_NAME} -f"
echo "   2. API test: curl https://${API_DOMAIN}/api/v1/"
echo "   3. Frontend test: curl https://${FRONTEND_DOMAIN}/"
echo "   4. Loopback port ${BACKEND_PORT}: phoenix-backend.service (gunicorn --bind) va nginx api proxy_pass mos kelishi kerak"
echo ""
echo "💾 Backup joylashuvi: ${DEPLOY_DIR}/backups/"
echo ""
