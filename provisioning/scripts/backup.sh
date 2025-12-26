#!/bin/bash

#===============================================================================
# iFin Bank - Database Backup Script
#===============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROVISIONING_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_DIR="$(dirname "$PROVISIONING_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

cd "$PROVISIONING_DIR"

echo "Creating database backup..."

# Backup PostgreSQL
docker-compose exec -T db pg_dump -U ifinbank ifinbank > "$BACKUP_DIR/ifinbank_$TIMESTAMP.sql"

# Compress
gzip "$BACKUP_DIR/ifinbank_$TIMESTAMP.sql"

echo "Backup created: $BACKUP_DIR/ifinbank_$TIMESTAMP.sql.gz"

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

echo "Cleanup complete. Keeping backups from last 7 days."

# List backups
echo ""
echo "Available backups:"
ls -lh "$BACKUP_DIR"/*.sql.gz 2>/dev/null || echo "No backups found"
