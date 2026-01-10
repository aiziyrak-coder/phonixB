#!/bin/bash
# Fix .env CORS settings

cd /phonix/backend

echo "🔧 Fixing .env CORS settings..."

# Backup .env
cp .env .env.backup

# Remove all CORS lines
sed -i '/^CORS_ALLOW_ALL_ORIGINS=/d' .env
sed -i '/^# CORS/d' .env
sed -i '/^CORS_ALLOWED_ORIGINS=/d' .env

# Add correct CORS settings at the end
cat >> .env << 'EOF'

# CORS Settings
CORS_ALLOW_ALL_ORIGINS=False
CORS_ALLOWED_ORIGINS=https://ilmiyfaoliyat.uz,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
EOF

echo "✅ .env file updated"
echo ""
echo "📋 CORS settings in .env:"
grep CORS .env

echo ""
echo "🔄 Restarting backend service..."
sudo systemctl restart phoenix-backend
sleep 3

echo ""
echo "🧪 Testing CORS settings..."
source venv/bin/activate
export $(cat .env | grep -v '^#' | xargs)
python manage.py shell << 'PYTHON'
from django.conf import settings
print("CORS_ALLOW_ALL_ORIGINS:", settings.CORS_ALLOW_ALL_ORIGINS)
print("CORS_ALLOWED_ORIGINS:", settings.CORS_ALLOWED_ORIGINS)
PYTHON
deactivate

echo ""
echo "✅ Done! If CORS_ALLOW_ALL_ORIGINS is still True, check settings.py"
