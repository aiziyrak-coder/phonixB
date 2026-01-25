#!/bin/bash
# Properly fix CORS by removing duplicate headers from Nginx
# Keep Nginx structure intact, just remove CORS headers

echo "=== Properly Fixing CORS Headers ==="
echo ""

NGINX_CONFIG="/etc/nginx/sites-available/api-ilmiyfaoliyat.conf"

if [ ! -f "$NGINX_CONFIG" ]; then
    echo "ERROR: Nginx config file not found at $NGINX_CONFIG"
    exit 1
fi

# Backup
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✓ Backup created"

# Create a Python script to properly edit the Nginx config
sudo python3 << 'PYTHON_SCRIPT'
import re
import sys

config_path = "/etc/nginx/sites-available/api-ilmiyfaoliyat.conf"

try:
    with open(config_path, 'r') as f:
        content = f.read()
    
    # Remove CORS headers from location blocks (but keep structure)
    # Remove add_header lines for CORS
    content = re.sub(r'\s+add_header\s+[\'"]Access-Control-Allow-Origin[\'"].*?;\s*\n', '', content)
    content = re.sub(r'\s+add_header\s+[\'"]Access-Control-Allow-Methods[\'"].*?;\s*\n', '', content)
    content = re.sub(r'\s+add_header\s+[\'"]Access-Control-Allow-Headers[\'"].*?;\s*\n', '', content)
    content = re.sub(r'\s+add_header\s+[\'"]Access-Control-Allow-Credentials[\'"].*?;\s*\n', '', content)
    content = re.sub(r'\s+add_header\s+[\'"]Access-Control-Max-Age[\'"].*?;\s*\n', '', content)
    
    # Remove OPTIONS if block that returns 204 (let Django handle it)
    # Match the entire if block for OPTIONS
    content = re.sub(
        r'\s+if\s+\(\$request_method\s+=\s+[\'"]OPTIONS[\'"]\)\s*\{[^}]*return\s+204;[^}]*\}\s*\n',
        '',
        content,
        flags=re.MULTILINE | re.DOTALL
    )
    
    with open(config_path, 'w') as f:
        f.write(content)
    
    print("✓ Removed CORS headers from Nginx")
    print("  Django CORS middleware will handle all CORS")
    sys.exit(0)
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
PYTHON_SCRIPT

if [ $? -ne 0 ]; then
    echo "✗ Failed to update Nginx config"
    echo "Restoring backup..."
    sudo cp "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONFIG"
    exit 1
fi

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
echo "=== CORS Fix Complete ==="
echo "Django CORS middleware will now handle all CORS including OPTIONS preflight"
