#!/usr/bin/env bash
# ==============================================================================
# Nightly Automated PostgreSQL Database Backup Script for Reply.BD
# Retains rolling 7-day backups with compressed custom format (-Fc).
# ==============================================================================

set -euo pipefail

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/replybd}"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_FILE="${BACKUP_DIR}/replybd_backup_${TIMESTAMP}.dump"
LOG_FILE="${BACKUP_DIR}/backup.log"
RETENTION_DAYS=7

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting automated PostgreSQL backup..." | tee -a "${LOG_FILE}"

# Source environment variables if .env file exists
if [ -f "/opt/replybd/.env" ]; then
    export $(grep -v '^#' /opt/replybd/.env | xargs)
fi

DB_USER="${POSTGRES_USER:-replybd_user}"
DB_NAME="${POSTGRES_DB:-replybd_db}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"

export PGPASSWORD="${POSTGRES_PASSWORD:-}"

# Perform dump using PostgreSQL's binary compressed custom format (-Fc)
# Custom format supports selective restore, parallel restore, and pgvector extension types
if pg_dump -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -F c -b -v -f "${BACKUP_FILE}" "${DB_NAME}" >> "${LOG_FILE}" 2>&1; then
    BACKUP_SIZE="$(du -h "${BACKUP_FILE}" | cut -f1)"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup SUCCESSFUL: ${BACKUP_FILE} (Size: ${BACKUP_SIZE})" | tee -a "${LOG_FILE}"
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: Backup failed for ${DB_NAME}!" | tee -a "${LOG_FILE}" >&2
    exit 1
fi

# Prune backups older than 7 days
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Purging backups older than ${RETENTION_DAYS} days..." | tee -a "${LOG_FILE}"
find "${BACKUP_DIR}" -type f -name "replybd_backup_*.dump" -mtime +"${RETENTION_DAYS}" -exec rm -f {} \;

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Backup lifecycle completed successfully." | tee -a "${LOG_FILE}"
