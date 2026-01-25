#!/bin/bash
# Fix CORS OPTIONS preflight requests
# Ensure OPTIONS requests get proper CORS headers while avoiding duplicates

echo "=== Fixing CORS OPTIONS Preflight ==="
echo ""

NGINX_CONFIG="/etc/nginx/sites-available/api-ilmiyfaoliyat.conf"

if [ ! -f "$NGINX_CONFIG" ]; then
    echo "ERROR: Nginx config file not found at $NGINX_CONFIG"
    exit 1
fi

# Backup
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backup created"

# The issue is that Django CORS middleware should handle OPTIONS, but we need to ensure
# Nginx doesn't interfere. Let's check the current config and ensure OPTIONS are handled by Django

# Remove all CORS headers from Nginx (Django will handle everything)
# But we need to ensure OPTIONS requests reach Django

echo "Removing all CORS headers from Nginx..."
echo "Django CORS middleware will handle all CORS including OPTIONS preflight"

# Remove CORS headers from all location blocks
sudo sed -i '/add_header.*Access-Control-Allow-Origin/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Allow-Methods/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Allow-Headers/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Allow-Credentials/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Max-Age/d' "$NGINX_CONFIG"

# Remove OPTIONS if block that returns 204 - let Django handle it
sudo sed -i '/if ($request_method = '\''OPTIONS'\'')/,/return 204;/d' "$NGINX_CONFIG"

echo "✓ Removed all CORS headers and OPTIONS handling from Nginx"
echo "  Django CORS middleware will handle everything"

# Test Nginx configuration
echo ""
echo "Testing Nginx configuration..."
if sudo nginx -t; then
    echo "✓ Nginx configuration is valid"
    
    # Reload Nginx
    echo ""
    echo "Reloading Nginx..."
    sudo systemctl reload nginx
    echo "✓ Nginx reloaded"
else
    echo "✗ Nginx configuration test failed"
    echo "Restoring backup..."
    sudo cp "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONFIG"
    exit 1
fi

echo ""
echo "=== CORS OPTIONS Fix Complete ==="
echo "Django CORS middleware will now handle all CORS including OPTIONS preflight"
echo ""
echo "If issues persist, check Django CORS middleware configuration:"
echo "  - CORS_ALLOWED_ORIGINS should include 'https://ilmiyfaoliyat.uz'"
echo "  - CORS_ALLOW_CREDENTIALS should be True"
echo "  - corsheaders.middleware.CorsMiddleware should be in MIDDLEWARE"
