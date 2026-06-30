#!/usr/bin/env bash
# Verify a PostgreSQL backup file can be listed and is non-empty.
set -euo pipefail

BACKUP_FILE="${1:-}"

if [ -z "${BACKUP_FILE}" ]; then
  echo "Usage: $0 <backup-file.sql.gz>" >&2
  exit 1
fi

if [ ! -f "${BACKUP_FILE}" ]; then
  echo "Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

if [ ! -s "${BACKUP_FILE}" ]; then
  echo "Backup file is empty: ${BACKUP_FILE}" >&2
  exit 1
fi

gzip -t "${BACKUP_FILE}"
echo "Backup verification passed: ${BACKUP_FILE}"
