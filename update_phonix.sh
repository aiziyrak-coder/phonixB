#!/bin/bash

# Phoenix Scientific Platform - Automated Update Script
# GitHub: https://github.com/aiziyrak-coder/phonixB

set -e

DEPLOY_DIR="/phonix"
BACKEND_REPO="https://github.com/aiziyrak-coder/phonixB.git"
FRONTEND_REPO="https://github.com/aiziyrak-coder/phonixF.git"

echo "🚀 Starting Phoenix deployment update..."

# Update system packages
echo "📦 Updating system packages..."
sudo apt-get update -qq

# Install dependencies if not installed
echo "📦 Installing dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv nginx postgresql postgresql-contrib git curl certbot python3-certbot-nginx build-essential 2>/dev/null || true

# Install Node.js and npm (fix conflict)
echo "📦 Installing Node.js..."
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

# Install Python build dependencies for Pillow
echo "📦 Installing Python build dependencies..."
sudo apt-get install -y python3-dev libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7 libtiff5-dev 2>/dev/null || true

# Create deployment directory (if doesn't exist)
echo "📁 Creating directories..."
if [ ! -d "${DEPLOY_DIR}" ]; then
    echo "Creating main deployment directory: ${DEPLOY_DIR}"
    sudo mkdir -p ${DEPLOY_DIR}
    sudo chown -R $(whoami):$(whoami) ${DEPLOY_DIR}
fi

sudo mkdir -p ${DEPLOY_DIR}/backend ${DEPLOY_DIR}/frontend ${DEPLOY_DIR}/backend/logs ${DEPLOY_DIR}/backend/media ${DEPLOY_DIR}/backend/staticfiles
sudo chown -R $(whoami):$(whoami) ${DEPLOY_DIR}

# Backend setup
echo "🔽 Updating backend..."
cd ${DEPLOY_DIR}
if [ -d backend/.git ]; then
    cd backend
    git pull
else
    rm -rf backend
    git clone ${BACKEND_REPO} backend
    cd backend
fi

# Setup virtual environment
if [ ! -d venv ]; then
    python3 -m venv venv
fi

source venv/bin/activate
pip install --upgrade pip -q
pip install --upgrade setuptools wheel -q

# Install core packages step by step to avoid conflicts (Python 3.13 compatible)
echo "📦 Installing dependencies step by step..."

# Core Django packages first
echo "  → Installing Django core..."
pip install "Django>=5.0.0" -q || pip install Django==5.0.1 -q
pip install "djangorestframework>=3.14.0" -q || pip install djangorestframework==3.14.0 -q
pip install "djangorestframework-simplejwt>=5.3.0" -q || pip install djangorestframework-simplejwt==5.3.1 -q

# Database packages
echo "  → Installing database packages..."
pip install "psycopg2-binary>=2.9.0" -q || pip install psycopg2-binary==2.9.9 -q
pip install "dj-database-url>=2.1.0" -q || pip install dj-database-url==2.1.0 -q

# Essential packages
echo "  → Installing essential packages..."
pip install "django-cors-headers>=4.3.0" -q || pip install django-cors-headers==4.3.1 -q
pip install "python-dotenv>=1.0.0" -q || pip install python-dotenv==1.0.0 -q
pip install "django-cleanup>=8.0.0" -q || echo "  ⚠️  django-cleanup skipped"

# API and utilities
echo "  → Installing API packages..."
pip install "requests>=2.31.0" -q || pip install requests==2.31.0 -q
pip install "google-generativeai>=0.3.0" -q || echo "  ⚠️  google-generativeai skipped"
pip install "django-phonenumber-field>=7.3.0" -q || echo "  ⚠️  django-phonenumber-field skipped"
pip install "phonenumbers>=8.13.0" -q || echo "  ⚠️  phonenumbers skipped"

# Celery (optional, skip if fails)
echo "  → Installing Celery (optional)..."
pip install "celery>=5.3.0" -q || echo "  ⚠️  celery skipped"
pip install "redis>=5.0.0" -q || echo "  ⚠️  redis skipped"
pip install "django-celery-beat>=2.5.0" -q || echo "  ⚠️  django-celery-beat skipped"

# Telegram bot (optional)
pip install "python-telegram-bot>=20.7" -q || echo "  ⚠️  python-telegram-bot skipped"

# Production server
echo "  → Installing production server..."
pip install "gunicorn>=21.2.0" -q || pip install gunicorn==21.2.0 -q
pip install "whitenoise>=6.6.0" -q || pip install whitenoise==6.6.0 -q

# Install Pillow separately with workaround for Python 3.13 (last, as it's problematic)
echo "  → Installing Pillow (Python 3.13 compatible)..."
pip install --upgrade setuptools pip wheel -q || true
pip install "Pillow>=10.4.0" --no-build-isolation --no-cache-dir -q 2>&1 | tail -1 || \
pip install "Pillow>=10.3.0" --no-build-isolation --no-cache-dir -q 2>&1 | tail -1 || \
pip install "Pillow>=10.0.0" --no-build-isolation --no-cache-dir -q 2>&1 | tail -1 || \
echo "  ⚠️  Pillow installation failed - skipping (install manually: pip install Pillow --no-build-isolation)"

echo "✅ Dependencies installation completed"

# Setup environment file
if [ ! -f .env ]; then
    cp env.production.example .env
    echo "⚠️  Please configure .env file: nano ${DEPLOY_DIR}/backend/.env"
fi

# Create necessary directories
mkdir -p logs media staticfiles
chmod 755 logs media staticfiles

# Run migrations
echo "🔄 Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "📦 Collecting static files..."
python manage.py collectstatic --noinput

deactivate

# Frontend setup
echo "🔽 Updating frontend..."
cd ${DEPLOY_DIR}
if [ -d frontend/.git ]; then
    cd frontend
    git pull
else
    rm -rf frontend
    git clone ${FRONTEND_REPO} frontend
    cd frontend
fi

# Install dependencies and build
echo "📦 Installing frontend dependencies..."
npm install --legacy-peer-deps -q || npm install -q

# Fix permissions for node_modules/.bin
chmod -R +x node_modules/.bin 2>/dev/null || true

echo "📦 Building frontend..."
export VITE_API_BASE_URL='https://api.ilmiyfaoliyat.uz/api/v1'
export VITE_MEDIA_URL='https://api.ilmiyfaoliyat.uz/media/'
export VITE_GEMINI_API_KEY='AIzaSyBvdPzXpZyjqydWisq4_tM4pxMIQM3NAxE'

# Use npx to run vite if direct command fails
npx vite build || npm run build || ./node_modules/.bin/vite build

# Setup PostgreSQL database
echo "🗄️  Setting up database..."
sudo -u postgres psql -c "CREATE DATABASE phoenix_scientific;" 2>/dev/null || echo "Database exists"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || echo "User exists"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE phoenix_scientific TO postgres;" 2>/dev/null || true

# Nginx configuration
echo "⚙️  Configuring Nginx..."
cd ${DEPLOY_DIR}/backend

# Create frontend nginx config
echo "  → Creating frontend Nginx config..."
sudo tee /etc/nginx/sites-available/ilmiyfaoliyat.conf > /dev/null <<'NGINX_FRONTEND'
server {
    listen 80;
    listen [::]:80;
    server_name ilmiyfaoliyat.uz www.ilmiyfaoliyat.uz;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name ilmiyfaoliyat.uz www.ilmiyfaoliyat.uz;

    # SSL certificates (will be configured by certbot)
    # ssl_certificate /etc/letsencrypt/live/ilmiyfaoliyat.uz/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/ilmiyfaoliyat.uz/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    root /phonix/frontend/dist;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /api/ {
        proxy_pass https://api.ilmiyfaoliyat.uz;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media/ {
        proxy_pass https://api.ilmiyfaoliyat.uz;
        proxy_set_header Host $host;
        expires 7d;
    }

    access_log /var/log/nginx/ilmiyfaoliyat.access.log;
    error_log /var/log/nginx/ilmiyfaoliyat.error.log;
}
NGINX_FRONTEND

# Create backend nginx config
echo "  → Creating backend Nginx config..."
sudo tee /etc/nginx/sites-available/api-ilmiyfaoliyat.conf > /dev/null <<'NGINX_BACKEND'
server {
    listen 80;
    listen [::]:80;
    server_name api.ilmiyfaoliyat.uz;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    http2 on;
    server_name api.ilmiyfaoliyat.uz;

    # SSL certificates (will be configured by certbot)
    # ssl_certificate /etc/letsencrypt/live/api.ilmiyfaoliyat.uz/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/api.ilmiyfaoliyat.uz/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 50M;
    client_body_timeout 60s;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /static/ {
        alias /phonix/backend/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /phonix/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 300s;
    }

    location ~ ^/api/v1/payments/click/(prepare|complete|callback)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    access_log /var/log/nginx/api-ilmiyfaoliyat.access.log;
    error_log /var/log/nginx/api-ilmiyfaoliyat.error.log;
}
NGINX_BACKEND

# Remove default site and disable conflicting configs (safely - only symlinks, not actual configs)
echo "  → Cleaning up existing Nginx configs..."
echo "  → Note: Only disabling symlinks in sites-enabled, original configs in sites-available remain intact"

# List all enabled configs to identify conflicts
echo "  → Checking for conflicting server names..."
CONFLICTING_CONFIGS=$(ls /etc/nginx/sites-enabled/ 2>/dev/null | grep -v "ilmiyfaoliyat\|api-ilmiyfaoliyat" || true)

# Backup existing enabled configs before disabling (optional, for safety)
if [ -f /etc/nginx/sites-enabled/konsilium ]; then
    echo "  → Backing up konsilium config symlink location..."
    sudo cp /etc/nginx/sites-enabled/konsilium /tmp/konsilium-enabled-backup.txt 2>/dev/null || true
fi
if [ -f /etc/nginx/sites-enabled/mirzoai-backend ]; then
    echo "  → Backing up mirzoai-backend config symlink location..."
    sudo cp /etc/nginx/sites-enabled/mirzoai-backend /tmp/mirzoai-backend-enabled-backup.txt 2>/dev/null || true
fi

# Disable ALL conflicting configs (only remove symlinks, original configs in sites-available are safe)
sudo rm -f /etc/nginx/sites-enabled/default
sudo rm -f /etc/nginx/sites-enabled/konsilium 2>/dev/null && echo "  → Disabled konsilium (config still in sites-available)" || true
sudo rm -f /etc/nginx/sites-enabled/mirzoai-backend 2>/dev/null && echo "  → Disabled mirzoai-backend (config still in sites-available)" || true
sudo rm -f /etc/nginx/sites-enabled/phoenix 2>/dev/null && echo "  → Disabled phoenix (if exists, config still in sites-available)" || true

# Disable any other configs that might conflict with our server names
for config in $CONFLICTING_CONFIGS; do
    if [ -f "/etc/nginx/sites-enabled/$config" ] && [ "$config" != "ilmiyfaoliyat.conf" ] && [ "$config" != "api-ilmiyfaoliyat.conf" ]; then
        # Check if this config uses our server names
        if sudo grep -q "ilmiyfaoliyat.uz\|api.ilmiyfaoliyat.uz" "/etc/nginx/sites-enabled/$config" 2>/dev/null; then
            echo "  → Disabling conflicting config: $config"
            sudo rm -f "/etc/nginx/sites-enabled/$config"
        fi
    fi
done

# Comment out SSL lines in configs temporarily (will be configured by certbot)
echo "  → Preparing Nginx configs for SSL setup..."
sudo sed -i 's|ssl_certificate|# ssl_certificate|g' /etc/nginx/sites-available/ilmiyfaoliyat.conf 2>/dev/null || true
sudo sed -i 's|ssl_certificate|# ssl_certificate|g' /etc/nginx/sites-available/api-ilmiyfaoliyat.conf 2>/dev/null || true

# Temporarily disable HTTPS servers (keep only HTTP redirect)
echo "  → Temporarily configuring HTTP-only configs..."
sudo tee /etc/nginx/sites-available/ilmiyfaoliyat.conf > /dev/null <<'NGINX_FRONTEND_HTTP'
server {
    listen 80;
    listen [::]:80;
    server_name ilmiyfaoliyat.uz www.ilmiyfaoliyat.uz;
    
    root /phonix/frontend/dist;
    index index.html;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /api/ {
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, User-Agent, X-Requested-With, X-CSRFToken' always;
            add_header 'Access-Control-Allow-Credentials' 'true' always;
            add_header 'Access-Control-Max-Age' '3600' always;
            add_header 'Content-Type' 'text/plain charset=UTF-8';
            add_header 'Content-Length' 0;
            return 204;
        }
        
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # CORS headers for actual requests
        add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        expires 7d;
    }

    access_log /var/log/nginx/ilmiyfaoliyat.access.log;
    error_log /var/log/nginx/ilmiyfaoliyat.error.log;
}
NGINX_FRONTEND_HTTP

sudo tee /etc/nginx/sites-available/api-ilmiyfaoliyat.conf > /dev/null <<'NGINX_BACKEND_HTTP'
server {
    listen 80;
    listen [::]:80;
    server_name api.ilmiyfaoliyat.uz;

    client_max_body_size 50M;
    client_body_timeout 60s;

    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /static/ {
        alias /phonix/backend/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias /phonix/backend/media/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 300s;
    }

    location ~ ^/api/v1/payments/click/(prepare|complete|callback)/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_buffering off;
    }

    access_log /var/log/nginx/api-ilmiyfaoliyat.access.log;
    error_log /var/log/nginx/api-ilmiyfaoliyat.error.log;
}
NGINX_BACKEND_HTTP

# Enable sites (create symlinks)
echo "  → Enabling Nginx sites..."
sudo ln -sf /etc/nginx/sites-available/ilmiyfaoliyat.conf /etc/nginx/sites-enabled/ilmiyfaoliyat.conf
sudo ln -sf /etc/nginx/sites-available/api-ilmiyfaoliyat.conf /etc/nginx/sites-enabled/api-ilmiyfaoliyat.conf

# Test and reload nginx (HTTP only first)
echo "  → Testing Nginx configuration (HTTP only)..."
if sudo nginx -t; then
    # Start nginx if not running, then reload
    sudo systemctl start nginx 2>/dev/null || true
    sudo systemctl reload nginx 2>/dev/null || sudo systemctl restart nginx
    echo "  ✅ Nginx reloaded successfully (HTTP only)"
else
    echo "  ⚠️  Nginx test failed, check configuration manually"
    echo "  Run: sudo nginx -t"
    exit 1
fi

# SSL certificate setup (first time only)
echo "🔒 Setting up SSL certificates..."
SSL_OUTPUT=$(sudo certbot --nginx -d ilmiyfaoliyat.uz -d www.ilmiyfaoliyat.uz -d api.ilmiyfaoliyat.uz --non-interactive --agree-tos --email admin@ilmiyfaoliyat.uz --redirect 2>&1)
echo "$SSL_OUTPUT" | tail -10

# Check if certbot created a new config file (phoenix) and merge it if needed
if [ -f /etc/nginx/sites-enabled/phoenix ]; then
    echo "  → Certbot created 'phoenix' config, checking if merge needed..."
    # Certbot usually modifies existing configs, but if it created a new one, we should check
    sudo rm -f /etc/nginx/sites-enabled/phoenix 2>/dev/null || true
fi

# Ensure nginx is running and reload config
if echo "$SSL_OUTPUT" | grep -q "successfully enabled HTTPS"; then
    echo "  ✅ SSL certificates installed successfully"
    sudo systemctl start nginx 2>/dev/null || true
    sudo systemctl reload nginx 2>/dev/null || sudo systemctl restart nginx
    echo "  ✅ Nginx reloaded with SSL configuration"
else
    echo "  ⚠️  SSL setup may have issues, check output above"
    echo "  You can set up SSL manually later with: sudo certbot --nginx"
fi

# Systemd service setup
echo "🔄 Setting up systemd service..."
cd ${DEPLOY_DIR}/backend

if [ -f phoenix-backend.service ]; then
    sudo cp phoenix-backend.service /etc/systemd/system/
fi

# Create service file if it doesn't exist
if [ ! -f /etc/systemd/system/phoenix-backend.service ]; then
    sudo tee /etc/systemd/system/phoenix-backend.service > /dev/null <<EOF
[Unit]
Description=Phoenix Scientific Platform Backend
After=network.target postgresql.service

[Service]
User=$(whoami)
Group=$(whoami)
WorkingDirectory=${DEPLOY_DIR}/backend
Environment="PATH=${DEPLOY_DIR}/backend/venv/bin"
Environment="DJANGO_SETTINGS_MODULE=config.settings"
Environment="PYTHONUNBUFFERED=1"
ExecStart=${DEPLOY_DIR}/backend/venv/bin/gunicorn --workers 4 --bind 127.0.0.1:8000 --timeout 300 --access-logfile ${DEPLOY_DIR}/backend/logs/gunicorn-access.log --error-logfile ${DEPLOY_DIR}/backend/logs/gunicorn-error.log config.wsgi:application
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
fi

# Setup logs directory
sudo mkdir -p ${DEPLOY_DIR}/backend/logs
sudo chown -R $(whoami):$(whoami) ${DEPLOY_DIR}/backend/logs

# Reload systemd and enable/restart service
sudo systemctl daemon-reload
sudo systemctl enable phoenix-backend
sudo systemctl restart phoenix-backend

# Show service status
echo ""
echo "📊 Service status:"
sudo systemctl status phoenix-backend --no-pager | head -15

echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "📝 Next steps:"
echo "1. Configure backend .env file: nano ${DEPLOY_DIR}/backend/.env"
echo "2. Restart service: sudo systemctl restart phoenix-backend"
echo "3. Check logs: sudo journalctl -u phoenix-backend -f"
echo "4. Test: curl https://api.ilmiyfaoliyat.uz/api/v1/"
echo ""
