#!/bin/bash
# Container entrypoint for web, worker, beat, and maintenance commands.
set -euo pipefail

log() {
    echo "[entrypoint] $*"
}

run_migrations() {
    log "Running database migrations..."
    python manage.py migrate --noinput
}

validate_config() {
    log "Validating environment configuration..."
    python manage.py validate_config
}

collect_static() {
    log "Collecting static files..."
    python manage.py collectstatic --noinput --clear
}

wait_for_dependencies() {
    if [ "${SKIP_WAIT_FOR_SERVICES:-false}" != "true" ]; then
        docker/wait-for-services.sh
    fi
}

start_gunicorn() {
    log "Starting Gunicorn..."
  exec gunicorn config.wsgi:application \
        --config docker/gunicorn.conf.py
}

COMMAND="${1:-gunicorn}"
shift || true

case "${COMMAND}" in
    web)
        wait_for_dependencies
        run_migrations
        log "Starting Django development server..."
        exec python manage.py runserver 0.0.0.0:8000
        ;;
    gunicorn)
        wait_for_dependencies
        validate_config
        run_migrations
        if [ "${COLLECT_STATIC_ON_START:-true}" = "true" ]; then
            collect_static
        fi
        start_gunicorn
        ;;
    celery-worker)
        wait_for_dependencies
        validate_config
        run_migrations
        log "Starting Celery worker..."
        exec celery -A config worker --loglevel="${CELERY_LOG_LEVEL:-info}"
        ;;
    celery-beat)
        wait_for_dependencies
        validate_config
        run_migrations
        log "Starting Celery beat..."
        exec celery -A config beat --loglevel="${CELERY_LOG_LEVEL:-info}" \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    migrate)
        wait_for_dependencies
        run_migrations
        ;;
    collectstatic)
        collect_static
        ;;
    validate-config)
        validate_config
        ;;
    *)
        exec "${COMMAND}" "$@"
        ;;
esac
