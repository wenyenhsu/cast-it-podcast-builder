#!/usr/bin/env bash
# Run database migrations.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ "${USE_DOCKER:-false}" = "true" ]; then
  docker compose exec web python manage.py migrate --noinput
else
  python manage.py migrate --noinput
fi

echo "Migrations complete."
