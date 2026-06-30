#!/bin/bash
# Wait for PostgreSQL and Redis before starting application processes.
set -euo pipefail

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

wait_for_postgres() {
    echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
    for _ in $(seq 1 60); do
        if python - <<'PY'
import os
import sys
import psycopg

host = os.environ.get("POSTGRES_HOST", "localhost")
port = os.environ.get("POSTGRES_PORT", "5432")
user = os.environ.get("POSTGRES_USER", "cast_it")
password = os.environ.get("POSTGRES_PASSWORD", "cast_it")
dbname = os.environ.get("POSTGRES_DB", "cast_it")

try:
    with psycopg.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        dbname=dbname,
        connect_timeout=3,
    ) as conn:
        conn.execute("SELECT 1")
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
        then
            echo "PostgreSQL is ready."
            return 0
        fi
        sleep 2
    done
    echo "PostgreSQL did not become ready in time." >&2
    return 1
}

wait_for_redis() {
    echo "Waiting for Redis at ${REDIS_URL}..."
    for _ in $(seq 1 30); do
        if python - <<'PY'
import os
import sys

try:
    import redis

    client = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"))
    client.ping()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
        then
            echo "Redis is ready."
            return 0
        fi
        sleep 2
    done
    echo "Redis did not become ready in time." >&2
    return 1
}

wait_for_postgres
wait_for_redis
