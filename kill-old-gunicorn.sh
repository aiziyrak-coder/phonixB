#!/bin/bash
# Kill old gunicorn processes that might be blocking port 8000
# This script is more aggressive but still tries to identify phoenix-backend processes

echo "=== Killing old gunicorn processes ==="
echo ""

# 1. Stop the service
echo "1. Stopping phoenix-backend service..."
sudo systemctl stop phoenix-backend
sleep 2

# 2. Find all gunicorn processes
echo "2. Finding all gunicorn processes..."
ALL_GUNICORN=$(pgrep -f "gunicorn" || echo "")

if [ -n "$ALL_GUNICORN" ]; then
    echo "   Found gunicorn processes: $ALL_GUNICORN"
    
    # Check each one
    for PID in $ALL_GUNICORN; do
        CMD=$(ps -p $PID -o cmd= 2>/dev/null || echo "")
        echo "   PID $PID: $CMD"
        
        # Check if it's using port 8000
        PORT_CHECK=$(sudo lsof -ti:8000 2>/dev/null | grep "^$PID$" || echo "")
        if [ -n "$PORT_CHECK" ]; then
            echo "   → PID $PID is using port 8000"
            
            # Check if it's phoenix-backend related
            if echo "$CMD" | grep -q "phonix\|phoenix\|config.wsgi"; then
                echo "   → Killing phoenix-backend process $PID"
                sudo kill -9 $PID 2>/dev/null || true
            else
                echo "   → PID $PID is NOT phoenix-backend related - checking working directory..."
                # Check working directory
                CWD=$(sudo readlink -f /proc/$PID/cwd 2>/dev/null || echo "")
                if echo "$CWD" | grep -q "phonix\|phoenix"; then
                    echo "   → Working directory suggests phoenix-backend: $CWD"
                    echo "   → Killing process $PID"
                    sudo kill -9 $PID 2>/dev/null || true
                else
                    echo "   → WARNING: PID $PID is NOT phoenix-backend related"
                    echo "   → NOT killing this process"
                fi
            fi
        fi
    done
    sleep 2
else
    echo "   No gunicorn processes found"
fi

# 3. Check port 8000 again
echo ""
echo "3. Checking port 8000 status..."
REMAINING=$(sudo lsof -ti:8000 2>/dev/null || echo "")
if [ -n "$REMAINING" ]; then
    echo "   WARNING: Port 8000 still in use by: $REMAINING"
    echo "   These processes are NOT phoenix-backend related"
else
    echo "   ✓ Port 8000 is now free"
fi

# 4. Start the service
echo ""
echo "4. Starting phoenix-backend service..."
sudo systemctl start phoenix-backend
sleep 3

# 5. Check status
echo ""
echo "5. Checking service status..."
if sudo systemctl is-active --quiet phoenix-backend; then
    echo "   ✓ phoenix-backend service is running"
    sudo systemctl status phoenix-backend --no-pager -l | head -10
else
    echo "   ✗ phoenix-backend service failed to start"
    echo "   Checking logs..."
    sudo journalctl -u phoenix-backend -n 20 --no-pager
fi

echo ""
echo "=== Complete ==="
