#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARCHIVE_PATH="$1"
FORCE_FLAG="$2"

if [ -z "$ARCHIVE_PATH" ]; then
    echo "Usage: ./scripts/restore.sh <path_to_backup_archive.tar.gz> [--force]"
    exit 1
fi

if [ ! -f "$ARCHIVE_PATH" ]; then
    echo "Error: Backup archive '$ARCHIVE_PATH' not found."
    exit 1
fi

echo "=== RUBY System Restore Utility ==="
echo "Target archive: $ARCHIVE_PATH"

# Check if Ruby server is running
PID_FILE="$DIR/.ruby.pid"
if [ "$FORCE_FLAG" != "--force" ] && [ -z "$FORCE_RESTORE" ] && [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Error: Ruby is currently running (PID $PID). Please run './stop.sh' before restoring (or pass --force)."
        exit 1
    fi
fi

cd "$DIR"

# Create a safety backup of existing data if present
if [ -d "data" ]; then
    SAFETY_BACKUP="data_pre_restore_$(date +%Y%m%d_%H%M%S)"
    echo "Backing up current data directory to '$SAFETY_BACKUP' before restore..."
    cp -r "data" "$SAFETY_BACKUP"
fi

echo "Extracting backup archive..."
tar -xzf "$ARCHIVE_PATH"

echo "Verifying restoration integrity..."
if [ -f "data/ruby.db" ]; then
    echo "✓ SQLite database successfully restored."
fi

if [ -d "data/chroma" ]; then
    echo "✓ ChromaDB vector store restored."
fi

if [ -d "data/documents" ]; then
    DOC_COUNT=$(find data/documents -type f | wc -l)
    echo "✓ Document store restored ($DOC_COUNT files)."
fi

echo "System restore completed successfully."
echo "You may now start Ruby with: ./start.sh"
