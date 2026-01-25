#!/bin/bash
# Fix duplicate CORS headers issue
# Remove CORS headers from Nginx and let Django handle them, OR vice versa

echo "=== Fixing Duplicate CORS Headers ==="
echo ""

NGINX_CONFIG="/etc/nginx/sites-available/api-ilmiyfaoliyat.conf"

if [ ! -f "$NGINX_CONFIG" ]; then
    echo "ERROR: Nginx config file not found at $NGINX_CONFIG"
    exit 1
fi

# Backup
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backup created"

# Option 1: Remove CORS headers from Nginx (let Django handle them)
# This is the recommended approach since Django CORS middleware is more flexible

echo "Removing CORS headers from Nginx (Django will handle them)..."
echo ""

# Remove CORS headers from location / block
sudo sed -i '/add_header.*Access-Control-Allow-Origin/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Allow-Methods/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Allow-Headers/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Allow-Credentials/d' "$NGINX_CONFIG"
sudo sed -i '/add_header.*Access-Control-Max-Age/d' "$NGINX_CONFIG"

# Keep only the OPTIONS preflight handling, but remove duplicate headers
# We'll keep the OPTIONS block but let Django handle the actual CORS headers

echo "✓ Removed CORS headers from Nginx"

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
echo "=== CORS Duplicate Fix Complete ==="
echo "Django CORS middleware will now handle all CORS headers"
echo "Nginx will only proxy requests without adding CORS headers"
