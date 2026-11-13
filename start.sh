#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.ruby.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Ruby is already running (PID $PID)."
        exit 0
    else
        rm -f "$PID_FILE"
    fi
fi

# Ensure data directory exists
mkdir -p "$DIR/data"

# Check if frontend is built
if [ ! -d "$DIR/frontend/dist" ]; then
    echo "Building frontend static assets..."
    cd "$DIR/frontend"
    npm run build
    cd "$DIR"
fi

echo "Starting Ruby server on http://127.0.0.1:8000 ..."
cd "$DIR/backend"
nohup .venv/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> "$DIR/data/ruby.log" 2>&1 &
SERVER_PID=$!
disown $SERVER_PID
echo "$SERVER_PID" > "$PID_FILE"
sleep 1.5

if ps -p "$SERVER_PID" > /dev/null 2>&1; then
    echo "Ruby started successfully (PID $SERVER_PID)."
    echo "Access Ruby at: http://127.0.0.1:8000"
    echo "API docs at:    http://127.0.0.1:8000/docs"
else
    echo "Ruby failed to start. Check $DIR/data/ruby.log for details."
    rm -f "$PID_FILE"
    exit 1
fi
