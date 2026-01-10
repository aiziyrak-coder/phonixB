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

# Create temporary requirements without Pillow
echo "📦 Preparing requirements..."
grep -v "^Pillow" requirements.txt > requirements_temp.txt || cp requirements.txt requirements_temp.txt

# Install requirements without Pillow first
echo "📦 Installing dependencies (without Pillow)..."
pip install -r requirements_temp.txt gunicorn -q

# Install Pillow separately with workaround for Python 3.13
echo "📦 Installing Pillow (Python 3.13 compatible version)..."
pip install --upgrade setuptools pip wheel -q || true

# Try multiple methods to install Pillow for Python 3.13
if pip install "Pillow>=10.4.0" --no-build-isolation --no-cache-dir -q 2>&1 | grep -q "Successfully installed"; then
    echo "✅ Pillow installed successfully"
elif pip install "Pillow>=10.3.0" --no-build-isolation --no-cache-dir -q 2>&1 | grep -q "Successfully installed"; then
    echo "✅ Pillow installed successfully"
elif pip install "Pillow>=10.0.0" --no-build-isolation --no-cache-dir -q 2>&1 | grep -q "Successfully installed"; then
    echo "✅ Pillow installed successfully"
else
    echo "⚠️  Pillow installation failed - skipping for now (can install manually later)"
    echo "   To install manually later, run: pip install Pillow --no-build-isolation"
fi

# Clean up
rm -f requirements_temp.txt

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
echo "📦 Building frontend..."
npm install -q

export VITE_API_BASE_URL='https://api.ilmiyfaoliyat.uz/api/v1'
export VITE_MEDIA_URL='https://api.ilmiyfaoliyat.uz/media/'

npm run build

# Setup PostgreSQL database
echo "🗄️  Setting up database..."
sudo -u postgres psql -c "CREATE DATABASE phoenix_scientific;" 2>/dev/null || echo "Database exists"
sudo -u postgres psql -c "CREATE USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || echo "User exists"
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'postgres';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE phoenix_scientific TO postgres;" 2>/dev/null || true

# Nginx configuration
echo "⚙️  Configuring Nginx..."
cd ${DEPLOY_DIR}/backend

# Copy nginx configs if they exist
if [ -f ilmiyfaoliyat.conf ]; then
    sudo cp ilmiyfaoliyat.conf /etc/nginx/sites-available/
fi

if [ -f api-ilmiyfaoliyat.conf ]; then
    sudo cp api-ilmiyfaoliyat.conf /etc/nginx/sites-available/
fi

# Enable sites
sudo ln -sf /etc/nginx/sites-available/ilmiyfaoliyat.conf /etc/nginx/sites-enabled/ 2>/dev/null || true
sudo ln -sf /etc/nginx/sites-available/api-ilmiyfaoliyat.conf /etc/nginx/sites-enabled/ 2>/dev/null || true
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
sudo nginx -t && sudo systemctl reload nginx

# SSL certificate setup (first time only)
echo "🔒 Setting up SSL certificates..."
sudo certbot --nginx -d ilmiyfaoliyat.uz -d www.ilmiyfaoliyat.uz -d api.ilmiyfaoliyat.uz --non-interactive --agree-tos --email admin@ilmiyfaoliyat.uz --redirect 2>&1 | tail -5 || echo "SSL setup skipped or already exists"

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
