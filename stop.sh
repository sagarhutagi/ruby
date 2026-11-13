#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$DIR/.ruby.pid"
SEARXNG_PID_FILE="$DIR/.searxng.pid"

# Stop SearXNG gateway if running
if [ -f "$SEARXNG_PID_FILE" ]; then
    SPID=$(cat "$SEARXNG_PID_FILE")
    if ps -p "$SPID" > /dev/null 2>&1; then
        echo "Stopping SearXNG Gateway ($SPID)..."
        kill "$SPID" 2>/dev/null || true
    fi
    rm -f "$SEARXNG_PID_FILE"
fi

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
