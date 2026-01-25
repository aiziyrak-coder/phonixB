#!/bin/bash
# Identify what processes are using port 8000

echo "=== Identifying processes on port 8000 ==="
echo ""

PORT_PIDS=$(sudo lsof -ti:8000 2>/dev/null || echo "")

if [ -z "$PORT_PIDS" ]; then
    echo "Port 8000 is free"
    exit 0
fi

echo "Processes using port 8000:"
echo ""

for PID in $PORT_PIDS; do
    echo "--- PID: $PID ---"
    ps -p $PID -o pid,ppid,user,cmd= 2>/dev/null || echo "Process not found"
    echo ""
done

echo ""
echo "=== Checking if any are phoenix-backend related ==="
echo ""

PHOENIX_FOUND=false
for PID in $PORT_PIDS; do
    CMD=$(ps -p $PID -o cmd= 2>/dev/null || echo "")
    if echo "$CMD" | grep -q "phonix\|phoenix\|config.wsgi"; then
        echo "PID $PID appears to be phoenix-backend related:"
        echo "  $CMD"
        PHOENIX_FOUND=true
    fi
done

if [ "$PHOENIX_FOUND" = false ]; then
    echo "No phoenix-backend processes found on port 8000"
    echo "These processes belong to other applications"
fi
