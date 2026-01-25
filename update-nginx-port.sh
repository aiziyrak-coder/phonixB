#!/bin/bash
# Update Nginx configuration to use new backend port (8003 instead of 8000)

echo "=== Updating Nginx configuration for new backend port ==="
echo ""

NEW_PORT=8003
NGINX_CONFIG="/etc/nginx/sites-available/api-ilmiyfaoliyat.conf"

# Check if config file exists
if [ ! -f "$NGINX_CONFIG" ]; then
    echo "ERROR: Nginx config file not found at $NGINX_CONFIG"
    echo "Please run fix-nginx-cors.sh first to create the config"
    exit 1
fi

# Backup the config
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backup created"

# Update port 8000 to 8003
sudo sed -i "s/proxy_pass http:\/\/127.0.0.1:8000;/proxy_pass http:\/\/127.0.0.1:$NEW_PORT;/g" "$NGINX_CONFIG"
echo "✓ Updated proxy_pass to port $NEW_PORT"

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
    
    # Check Nginx status
    if sudo systemctl is-active --quiet nginx; then
        echo "✓ Nginx is running"
    else
        echo "✗ Nginx is not running"
        exit 1
    fi
else
    echo "✗ Nginx configuration test failed"
    echo "Restoring backup..."
    sudo cp "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONFIG"
    exit 1
fi

echo ""
echo "=== Nginx Port Update Complete ==="
echo "Backend is now accessible on port $NEW_PORT"
