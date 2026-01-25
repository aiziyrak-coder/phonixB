#!/bin/bash
# Nginx CORS Configuration Fix
# Bu script Nginx konfiguratsiyasida CORS header'larni to'g'ri sozlaydi

set -e

echo "🔧 Nginx CORS konfiguratsiyasini tuzatish..."
echo ""

# 1. SSL sertifikat mavjudligini tekshirish
SSL_CERT_EXISTS=false
if [ -f /etc/letsencrypt/live/api.ilmiyfaoliyat.uz/fullchain.pem ]; then
    SSL_CERT_EXISTS=true
    echo "✅ SSL sertifikat topildi"
else
    echo "⚠️  SSL sertifikat topilmadi (HTTP-only config yaratiladi)"
fi

# 2. Nginx konfiguratsiyasini yaratish
if [ "$SSL_CERT_EXISTS" = true ]; then
    echo "  → HTTPS konfiguratsiyasini yaratish..."
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
        
        # CORS headers for actual requests (Django CORS middleware also adds these, but we ensure they're present)
        add_header 'Access-Control-Allow-Origin' 'https://ilmiyfaoliyat.uz' always;
        add_header 'Access-Control-Allow-Credentials' 'true' always;
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, User-Agent, X-Requested-With, X-CSRFToken' always;
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
    echo "  → HTTP-only konfiguratsiyasini yaratish..."
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
        add_header 'Access-Control-Allow-Methods' 'GET, POST, PUT, PATCH, DELETE, OPTIONS' always;
        add_header 'Access-Control-Allow-Headers' 'Authorization, Content-Type, Accept, Origin, User-Agent, X-Requested-With, X-CSRFToken' always;
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

# 3. Nginx konfiguratsiyasini test qilish
echo ""
echo "  → Nginx konfiguratsiyasini test qilish..."
if sudo nginx -t; then
    echo "  ✅ Nginx konfiguratsiyasi to'g'ri"
else
    echo "  ❌ Nginx konfiguratsiyasi xatolik!"
    sudo nginx -t 2>&1 | head -20
    exit 1
fi

# 4. Nginx'ni reload qilish
echo ""
echo "  → Nginx'ni reload qilish..."
sudo systemctl reload nginx
sleep 2

# 5. Nginx status tekshirish
echo ""
echo "  → Nginx status tekshirish..."
if sudo systemctl is-active --quiet nginx; then
    echo "  ✅ Nginx ishlayapti"
    sudo systemctl status nginx --no-pager | head -10
else
    echo "  ❌ Nginx ishlamayapti!"
    exit 1
fi

# 6. CORS test qilish
echo ""
echo "  → CORS test qilish..."
CORS_TEST=$(curl -s -I -H "Origin: https://ilmiyfaoliyat.uz" \
    -X OPTIONS https://api.ilmiyfaoliyat.uz/api/v1/auth/login/ 2>&1 | grep -i "access-control-allow-origin" || echo "NOT_FOUND")

if echo "$CORS_TEST" | grep -q "ilmiyfaoliyat.uz"; then
    echo "  ✅ CORS header to'g'ri: $CORS_TEST"
else
    echo "  ⚠️  CORS header topilmadi yoki noto'g'ri: $CORS_TEST"
fi

echo ""
echo "✅ Nginx CORS konfiguratsiyasi tuzatildi!"
