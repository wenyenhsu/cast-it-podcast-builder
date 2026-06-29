#!/bin/bash
set -e

run_migrations() {
    python manage.py migrate --noinput
}

if [ "$1" = "web" ]; then
    run_migrations
    exec python manage.py runserver 0.0.0.0:8000
elif [ "$1" = "celery-worker" ]; then
    run_migrations
    exec celery -A config worker --loglevel=info
elif [ "$1" = "celery-beat" ]; then
    run_migrations
    exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
elif [ "$1" = "gunicorn" ]; then
    run_migrations
    exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
else
    exec "$@"
fi
