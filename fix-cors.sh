#!/bin/bash
# Quick CORS fix script for server

echo "🔧 Fixing CORS configuration..."

# 1. Update backend .env file
cd /phonix/backend
if ! grep -q "CORS_ALLOWED_ORIGINS" .env 2>/dev/null; then
    echo "" >> .env
    echo "# CORS Settings" >> .env
    echo "CORS_ALLOW_ALL_ORIGINS=False" >> .env
    echo "CORS_ALLOWED_ORIGINS=https://ilmiyfaoliyat.uz,http://localhost:3000,http://127.0.0.1:3000" >> .env
    echo "✅ Added CORS settings to .env"
else
    echo "✅ CORS settings already exist in .env"
fi

# 2. Check if SSL certificates exist first
SSL_CERT_EXISTS=false
if [ -f /etc/letsencrypt/live/api.ilmiyfaoliyat.uz/fullchain.pem ]; then
    SSL_CERT_EXISTS=true
    echo "✅ SSL certificates found, creating HTTPS config..."
else
    echo "⚠️  SSL certificates not found, creating HTTP-only config first..."
fi

# 3. Update Nginx config based on SSL certificate availability
if [ "$SSL_CERT_EXISTS" = true ]; then
    # HTTPS config with SSL
    sudo tee /etc/nginx/sites-available/api-ilmiyfaoliyat.conf > /dev/null <<'EOF'
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

    ssl_certificate /etc/letsencrypt/live/api.ilmiyfaoliyat.uz/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.ilmiyfaoliyat.uz/privkey.pem;
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

    # Handle CORS preflight requests
    location / {
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
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 300s;
        
        # CORS headers for actual requests
        add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    location ~ ^/api/v1/payments/click/(prepare|complete|callback)/ {
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, User-Agent, X-Requested-With' always;
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
        proxy_read_timeout 300s;
        proxy_buffering off;
        
        add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    access_log /var/log/nginx/api-ilmiyfaoliyat.access.log;
    error_log /var/log/nginx/api-ilmiyfaoliyat.error.log;
}
EOF
else
    # HTTP-only config without SSL (for initial setup)
    sudo tee /etc/nginx/sites-available/api-ilmiyfaoliyat.conf > /dev/null <<'EOF_HTTP'
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
        proxy_set_header X-Forwarded-Host $host;
        proxy_read_timeout 300s;
        
        add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    location ~ ^/api/v1/payments/click/(prepare|complete|callback)/ {
        if ($request_method = 'OPTIONS') {
            add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
            add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
            add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, User-Agent, X-Requested-With' always;
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
        proxy_read_timeout 300s;
        proxy_buffering off;
        
        add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
    }

    access_log /var/log/nginx/api-ilmiyfaoliyat.access.log;
    error_log /var/log/nginx/api-ilmiyfaoliyat.error.log;
}
EOF_HTTP
fi

# 4. Test and reload Nginx
echo "🧪 Testing Nginx configuration..."
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo "✅ Nginx reloaded successfully"
else
    echo "❌ Nginx configuration test failed"
    echo "⚠️  Trying to check what's wrong..."
    sudo nginx -t 2>&1 | head -20
    exit 1
fi

# 5. If HTTP-only config was created, try to get SSL certificates
if [ "$SSL_CERT_EXISTS" = false ]; then
    echo "🔒 Attempting to get SSL certificates..."
    # Stop nginx temporarily for standalone mode
    sudo systemctl stop nginx
    
    # Get certificate using standalone mode
    if sudo certbot certonly --standalone -d api.ilmiyfaoliyat.uz --non-interactive --agree-tos --email admin@ilmiyfaoliyat.uz 2>&1 | tail -10; then
        echo "✅ SSL certificates obtained successfully"
        # Restart nginx
        sudo systemctl start nginx
        # Now regenerate config with SSL
        SSL_CERT_EXISTS=true
        echo "🔄 Regenerating Nginx config with SSL..."
        # Re-run the config creation with SSL
        ./fix-cors.sh
        exit 0
    else
        echo "⚠️  SSL certificate generation failed, continuing with HTTP-only"
        sudo systemctl start nginx
    fi
fi

# 6. Pull latest backend code
cd /phonix/backend
git pull

# 7. Check backend service errors first
echo "🔍 Checking backend service errors..."
sudo journalctl -u phoenix-backend --no-pager -n 20 | tail -10

# 8. Try to start backend manually to see errors
echo "🧪 Testing backend startup..."
cd /phonix/backend
source venv/bin/activate

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check Django
python manage.py check --deploy 2>&1 | head -30 || echo "⚠️  Django check failed"

# Try to run gunicorn manually to see errors
echo "🧪 Testing Gunicorn startup..."
timeout 5 gunicorn --workers 1 --bind 127.0.0.1:8000 --timeout 10 config.wsgi:application 2>&1 | head -30 || echo "⚠️  Gunicorn test completed (timeout expected)"

deactivate

# 9. Restart backend service
echo "🔄 Restarting backend service..."
sudo systemctl restart phoenix-backend
sleep 3
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "✅ Backend service is running"
    sudo systemctl status phoenix-backend --no-pager | head -10
else
    echo "❌ Backend service failed to start"
    echo "📋 Last 30 lines of logs:"
    sudo journalctl -u phoenix-backend --no-pager -n 30
fi

echo ""
echo "✅ CORS fix completed!"
echo "🧪 Test with: curl -X OPTIONS https://api.ilmiyfaoliyat.uz/api/v1/auth/login/ -H 'Origin: https://ilmiyfaoliyat.uz' -v"
