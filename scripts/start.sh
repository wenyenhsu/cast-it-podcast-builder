#!/usr/bin/env bash
# Start the local development Docker stack.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-.env}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Missing ${ENV_FILE}. Copy .env.example first." >&2
  exit 1
fi

COMPOSE=(docker compose -f "${COMPOSE_FILE}" --env-file "${ENV_FILE}")

echo "Starting Cast It development stack..."
"${COMPOSE[@]}" up --build -d

WEB_MAPPING=""
for _ in $(seq 1 30); do
  WEB_MAPPING="$("${COMPOSE[@]}" port web 8000 2>/dev/null || true)"
  if [ -n "${WEB_MAPPING}" ]; then
    break
  fi
  sleep 2
done

if [ -z "${WEB_MAPPING}" ]; then
  echo ""
  echo "Stack containers started, but the web port is not available yet."
  echo "Check status: docker compose ps"
  echo "View logs:    docker compose logs -f web"
  exit 1
fi

HOST_PORT="${WEB_MAPPING##*:}"
BASE_URL="http://localhost:${HOST_PORT}"

cat <<EOF

Cast It is running.

  API base:   ${BASE_URL}/api/v1/
  Health:     ${BASE_URL}/api/v1/health/live/
  API docs:   ${BASE_URL}/api/v1/docs/
  Dashboard:  ${BASE_URL}/
  Admin:      ${BASE_URL}/admin/
  Version:    ${BASE_URL}/api/v1/version/

Web port on host: ${HOST_PORT}
(Set WEB_PORT=8000 in .env for a fixed port.)

EOF
