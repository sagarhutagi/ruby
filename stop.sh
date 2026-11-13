#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.ruby.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "Ruby is not running (no PID file found)."
    exit 0
fi

PID=$(cat "$PID_FILE")
if ps -p "$PID" > /dev/null 2>&1; then
    echo "Stopping Ruby process $PID..."
    kill "$PID"
    sleep 1
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Force stopping Ruby..."
        kill -9 "$PID"
    fi
    echo "Ruby stopped successfully."
else
    echo "Process $PID not found; cleaning up PID file."
fi

rm -f "$PID_FILE"
