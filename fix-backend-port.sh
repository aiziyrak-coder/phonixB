#!/bin/bash
# Fix port 8000 conflict for phoenix-backend service only
# This script only kills processes related to phoenix-backend to avoid affecting other applications

echo "=== Fixing Port 8000 for phoenix-backend ==="
echo ""

# 1. Stop the service first
echo "1. Stopping phoenix-backend service..."
sudo systemctl stop phoenix-backend
sleep 2

# 2. Find and kill only phoenix-backend related processes on port 8000
echo "2. Finding processes using port 8000..."
PORT_PIDS=$(sudo lsof -ti:8000 2>/dev/null || echo "")

if [ -n "$PORT_PIDS" ]; then
    echo "   Found processes on port 8000: $PORT_PIDS"
    
    # Filter to only phoenix-backend related processes
    PHOENIX_PIDS=""
    for PID in $PORT_PIDS; do
        # Check if process is related to phoenix-backend
        CMD=$(ps -p $PID -o cmd= 2>/dev/null || echo "")
        if echo "$CMD" | grep -q "/phonix/backend" || echo "$CMD" | grep -q "gunicorn.*config.wsgi" || echo "$CMD" | grep -q "phoenix-backend"; then
            PHOENIX_PIDS="$PHOENIX_PIDS $PID"
        fi
    done
    
    if [ -n "$PHOENIX_PIDS" ]; then
        echo "   Killing phoenix-backend related processes: $PHOENIX_PIDS"
        echo "$PHOENIX_PIDS" | xargs -r sudo kill -9 2>/dev/null || true
        sleep 1
    else
        echo "   No phoenix-backend processes found on port 8000"
        echo "   WARNING: Port 8000 is used by other application. Not killing."
    fi
else
    echo "   No processes found on port 8000"
fi

# 3. Kill any remaining gunicorn processes related to phoenix-backend
echo "3. Checking for phoenix-backend gunicorn processes..."
PHOENIX_GUNICORN_PIDS=$(pgrep -f "gunicorn.*phonix.*backend" 2>/dev/null || pgrep -f "gunicorn.*config.wsgi" 2>/dev/null | xargs -I {} sh -c 'ps -p {} -o cmd= 2>/dev/null | grep -q "/phonix/backend" && echo {}' 2>/dev/null || echo "")

if [ -n "$PHOENIX_GUNICORN_PIDS" ]; then
    echo "   Found phoenix-backend gunicorn processes: $PHOENIX_GUNICORN_PIDS"
    echo "$PHOENIX_GUNICORN_PIDS" | xargs -r sudo kill -9 2>/dev/null || true
    sleep 1
else
    echo "   No phoenix-backend gunicorn processes found"
fi

# 4. Verify port 8000 is free (only for phoenix-backend)
echo "4. Verifying port 8000 status..."
REMAINING_PIDS=$(sudo lsof -ti:8000 2>/dev/null || echo "")
if [ -n "$REMAINING_PIDS" ]; then
    echo "   WARNING: Port 8000 is still in use by: $REMAINING_PIDS"
    echo "   These processes are NOT phoenix-backend related and will NOT be killed"
    echo "   Please check if you need to change phoenix-backend port or stop the other application manually"
else
    echo "   ✓ Port 8000 is now free"
fi

# 5. Start the service
echo "5. Starting phoenix-backend service..."
sudo systemctl start phoenix-backend
sleep 3

# 6. Check service status
echo "6. Checking service status..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "   ✓ phoenix-backend service is running"
    sudo systemctl status phoenix-backend --no-pager -l | head -10
else
    echo "   ✗ phoenix-backend service failed to start"
    echo "   Checking logs..."
    sudo journalctl -u phoenix-backend -n 20 --no-pager
fi

echo ""
echo "=== Fix Complete ==="
