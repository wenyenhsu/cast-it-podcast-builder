#!/usr/bin/env bash
# Start only web + db + redis (no Celery worker/beat).
# Use this for UI work when you do not need background jobs.
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

echo "Starting Cast It (lite: web + db + redis only)..."
"${COMPOSE[@]}" up --build -d db redis web

# Stop Celery if a full stack was running earlier.
"${COMPOSE[@]}" stop celery-worker celery-beat 2>/dev/null || true

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
  echo "Containers started, but the web port is not available yet."
  echo "Check status: docker compose ps"
  exit 1
fi

HOST_PORT="${WEB_MAPPING##*:}"
BASE_URL="http://localhost:${HOST_PORT}"

cat <<EOF

Cast It (lite) is running.

  Dashboard:  ${BASE_URL}/
  API:        ${BASE_URL}/api/v1/

Celery worker/beat are NOT running.
- Generate Script / TTS jobs will stay queued until you run: ./scripts/start.sh
- Saves ~900MB RAM vs the full stack.

Stop: ./scripts/stop.sh

EOF
