#!/usr/bin/env bash
# Collect static files for production deployment.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ "${USE_DOCKER:-false}" = "true" ]; then
  docker compose exec web python manage.py collectstatic --noinput --clear
else
  python manage.py collectstatic --noinput --clear
fi

echo "Static files collected."
