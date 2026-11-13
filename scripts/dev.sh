#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

echo "Starting Backend on http://127.0.0.1:8000 ..."
cd "$DIR/backend"
PYTHONPATH=. .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload &

echo "Starting Frontend dev server on http://127.0.0.1:5173 ..."
cd "$DIR/frontend"
npm run dev &

wait
