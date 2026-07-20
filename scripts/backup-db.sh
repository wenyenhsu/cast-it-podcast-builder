#!/usr/bin/env bash
# Create a PostgreSQL backup from the production compose stack.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE_FILE="${COMPOSE_FILE:-docker/deploy/docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-docker/deploy/.env.production}"
BACKUP_DIR="${BACKUP_DIR:-./backups/postgres}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
BACKUP_FILE="${BACKUP_DIR}/cast_it_${TIMESTAMP}.sql.gz"

mkdir -p "${BACKUP_DIR}"

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" exec -T db \
  pg_dump -U "${POSTGRES_USER:-cast_it}" "${POSTGRES_DB:-cast_it}" | gzip > "${BACKUP_FILE}"

echo "Backup created: ${BACKUP_FILE}"
