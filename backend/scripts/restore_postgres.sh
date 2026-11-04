#!/usr/bin/env bash
# ==============================================================================
# Database Restore Script for Reply.BD
# Restores a compressed PostgreSQL dump (-Fc) into the target database.
# Usage: ./restore_postgres.sh /path/to/replybd_backup_YYYYMMDD_HHMMSS.dump
# ==============================================================================

set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_file.dump> [target_database_name]"
    exit 1
fi

BACKUP_FILE="$1"
TARGET_DB="${2:-replybd_db}"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "ERROR: Backup file '${BACKUP_FILE}' not found!"
    exit 1
fi

echo "=================================================================="
echo "WARNING: This will drop existing connections and restore into: ${TARGET_DB}"
echo "Backup File: ${BACKUP_FILE}"
echo "=================================================================="
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
    echo "Restore aborted by user."
    exit 0
fi

# Source .env if present
if [ -f "/opt/replybd/.env" ]; then
    export $(grep -v '^#' /opt/replybd/.env | xargs)
fi

DB_USER="${POSTGRES_USER:-replybd_user}"
DB_HOST="${POSTGRES_HOST:-localhost}"
DB_PORT="${POSTGRES_PORT:-5432}"
export PGPASSWORD="${POSTGRES_PASSWORD:-}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Terminating active connections to ${TARGET_DB}..."
psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d postgres -c "
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${TARGET_DB}' AND pid <> pg_backend_pid();
" || true

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Restoring database from ${BACKUP_FILE}..."
pg_restore -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${TARGET_DB}" --clean --if-exists --no-owner --no-privileges -v "${BACKUP_FILE}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Database restore completed successfully!"
