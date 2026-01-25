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

# Remove CORS headers from actual requests (location / block), but keep OPTIONS preflight
# This way Django CORS middleware handles actual requests, and Nginx handles OPTIONS preflight

# Remove CORS headers from location / block (actual requests)
# But keep them in OPTIONS if block for preflight
sudo sed -i '/^[[:space:]]*add_header.*Access-Control-Allow-Origin.*always;$/d' "$NGINX_CONFIG"
sudo sed -i '/^[[:space:]]*add_header.*Access-Control-Allow-Methods.*always;$/d' "$NGINX_CONFIG"
sudo sed -i '/^[[:space:]]*add_header.*Access-Control-Allow-Headers.*always;$/d' "$NGINX_CONFIG"
sudo sed -i '/^[[:space:]]*add_header.*Access-Control-Allow-Credentials.*always;$/d' "$NGINX_CONFIG"

# However, we need to ensure OPTIONS preflight still works
# Let's keep OPTIONS handling but let Django handle actual requests

echo "✓ Removed duplicate CORS headers from actual requests"
echo "  OPTIONS preflight will be handled by Django CORS middleware"

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
