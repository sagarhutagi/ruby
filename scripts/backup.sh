#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${1:-$DIR/backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
ARCHIVE_PATH="$BACKUP_DIR/ruby_backup_$TIMESTAMP.tar.gz"

echo "=== RUBY System Backup Utility ==="
echo "Working directory: $DIR"
echo "Target archive:    $ARCHIVE_PATH"

if [ ! -d "$DIR/data" ]; then
    echo "Error: Data directory '$DIR/data' does not exist. Nothing to back up."
    exit 1
fi

# Files and directories to back up
ITEMS_TO_BACKUP=()
cd "$DIR"

if [ -f "data/ruby.db" ]; then
    if command -v sqlite3 >/dev/null 2>&1; then
        sqlite3 "data/ruby.db" "PRAGMA wal_checkpoint(TRUNCATE);" >/dev/null 2>&1 || true
    fi
    ITEMS_TO_BACKUP+=("data/ruby.db")
    if [ -f "data/ruby.db-wal" ]; then
        ITEMS_TO_BACKUP+=("data/ruby.db-wal")
    fi
    if [ -f "data/ruby.db-shm" ]; then
        ITEMS_TO_BACKUP+=("data/ruby.db-shm")
    fi
fi

if [ -d "data/chroma" ]; then
    ITEMS_TO_BACKUP+=("data/chroma")
fi

if [ -d "data/documents" ]; then
    ITEMS_TO_BACKUP+=("data/documents")
fi

if [ -f "data/.secrets.enc" ]; then
    ITEMS_TO_BACKUP+=("data/.secrets.enc")
fi

if [ -f ".env" ]; then
    ITEMS_TO_BACKUP+=(".env")
fi

if [ ${#ITEMS_TO_BACKUP[@]} -eq 0 ]; then
    echo "Warning: No databases or document stores found in 'data/'. Creating empty data backup."
    mkdir -p data
    ITEMS_TO_BACKUP+=("data")
fi

echo "Archiving: ${ITEMS_TO_BACKUP[*]} ..."
tar -czf "$ARCHIVE_PATH" "${ITEMS_TO_BACKUP[@]}"

BACKUP_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
echo "Backup created successfully: $ARCHIVE_PATH ($BACKUP_SIZE)"
echo "Done."
