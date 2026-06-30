#!/usr/bin/env bash
# Create a Django admin superuser.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if [ "${USE_DOCKER:-false}" = "true" ]; then
  docker compose exec web python manage.py createsuperuser
else
  python manage.py createsuperuser
fi
