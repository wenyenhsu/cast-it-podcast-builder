#!/usr/bin/env bash
# Run linting checks.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

ruff check .
mypy apps api config domain infrastructure services
