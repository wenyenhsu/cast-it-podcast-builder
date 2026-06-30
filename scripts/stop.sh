#!/usr/bin/env bash
# Stop Docker Compose services.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-.env}"

docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}" down
echo "Stack stopped."
