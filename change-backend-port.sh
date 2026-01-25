#!/bin/bash
# Change phoenix-backend port from 8000 to 8003 to avoid conflict with other applications

echo "=== Changing phoenix-backend port to 8003 ==="
echo ""

NEW_PORT=8003
OLD_PORT=8000

# 1. Check if new port is available
echo "1. Checking if port $NEW_PORT is available..."
if sudo lsof -ti:$NEW_PORT >/dev/null 2>&1; then
    echo "   WARNING: Port $NEW_PORT is already in use!"
    echo "   Please choose a different port or stop the application using port $NEW_PORT"
    exit 1
else
    echo "   ✓ Port $NEW_PORT is available"
fi

# 2. Stop the service
echo ""
echo "2. Stopping phoenix-backend service..."
sudo systemctl stop phoenix-backend
sleep 2

# 3. Update systemd service file
echo ""
echo "3. Updating systemd service file..."
SERVICE_FILE="/etc/systemd/system/phoenix-backend.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "   ERROR: Service file not found at $SERVICE_FILE"
    exit 1
fi

# Backup the service file
sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "   ✓ Backup created"

# Update the port in the service file
sudo sed -i "s/--bind 127.0.0.1:$OLD_PORT/--bind 127.0.0.1:$NEW_PORT/g" "$SERVICE_FILE"
echo "   ✓ Service file updated to use port $NEW_PORT"

# 4. Reload systemd and restart service
echo ""
echo "4. Reloading systemd and starting service..."
sudo systemctl daemon-reload
sudo systemctl start phoenix-backend
sleep 3

# 5. Check service status
echo ""
echo "5. Checking service status..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "   ✓ phoenix-backend service is running on port $NEW_PORT"
    sudo systemctl status phoenix-backend --no-pager -l | head -10
else
    echo "   ✗ phoenix-backend service failed to start"
    echo "   Checking logs..."
    sudo journalctl -u phoenix-backend -n 20 --no-pager
    exit 1
fi

# 6. Verify port
echo ""
echo "6. Verifying port $NEW_PORT..."
if sudo lsof -ti:$NEW_PORT >/dev/null 2>&1; then
    PORT_PID=$(sudo lsof -ti:$NEW_PORT)
    echo "   ✓ Port $NEW_PORT is in use by PID: $PORT_PID"
    
    # Check if it's phoenix-backend
    CMD=$(ps -p $PORT_PID -o cmd= 2>/dev/null || echo "")
    if echo "$CMD" | grep -q "phonix.*backend\|config.wsgi"; then
        echo "   ✓ Port is correctly used by phoenix-backend"
    else
        echo "   ⚠️  Port is used by a different process"
    fi
else
    echo "   ✗ Port $NEW_PORT is not in use - service may not be running correctly"
fi

echo ""
echo "=== Port Change Complete ==="
echo ""
echo "⚠️  IMPORTANT: You need to update Nginx configuration to proxy to port $NEW_PORT"
echo "   Update the proxy_pass directive in Nginx config for api.ilmiyfaoliyat.uz"
echo "   Change: proxy_pass http://127.0.0.1:$OLD_PORT;"
echo "   To:     proxy_pass http://127.0.0.1:$NEW_PORT;"
echo ""
echo "   Then run: sudo nginx -t && sudo systemctl reload nginx"
