.PHONY: up down build rebuild restart logs logs-web logs-worker logs-beat \
        shell bash migrate migrations createsuperuser collectstatic \
        db-shell redis-cli reset-db \
        import-news plan-episode generate-script generate-audio publish \
        youtube-token test test-fast

DC = docker compose

# ── Stack control ──────────────────────────────────────────────────────────────

up:
	$(DC) up -d

down:
	$(DC) down

build:
	$(DC) build

rebuild:
	$(DC) build --no-cache

restart:
	$(DC) restart

# ── Logs ───────────────────────────────────────────────────────────────────────

logs:
	$(DC) logs -f

logs-web:
	$(DC) logs -f web

logs-worker:
	$(DC) logs -f celery-worker

logs-beat:
	$(DC) logs -f celery-beat

# ── Django ─────────────────────────────────────────────────────────────────────

shell:
	$(DC) exec web python manage.py shell_plus

bash:
	$(DC) exec web bash

migrate:
	$(DC) exec web python manage.py migrate

migrations:
	$(DC) exec web python manage.py makemigrations

createsuperuser:
	$(DC) exec web python manage.py createsuperuser

collectstatic:
	$(DC) exec web python manage.py collectstatic --noinput

# ── Database ───────────────────────────────────────────────────────────────────

db-shell:
	$(DC) exec db psql -U cast_it -d cast_it

redis-cli:
	$(DC) exec redis redis-cli

reset-db:
	@echo "WARNING: This will drop and recreate the database."
	@read -p "Continue? [y/N] " ans && [ "$$ans" = "y" ]
	$(DC) down -v
	$(DC) up -d db redis
	sleep 3
	$(DC) up -d

# ── Pipeline (manual triggers) ─────────────────────────────────────────────────

import-news:
	$(DC) exec web python manage.py shell -c \
		"from apps.scheduler.tasks.import_news import import_news_scheduled; import_news_scheduled()"

plan-episode:
	$(DC) exec web python manage.py shell -c \
		"from apps.scheduler.tasks.planning import episode_planning_scheduled; episode_planning_scheduled()"

generate-audio:
	$(DC) exec web python manage.py shell -c \
		"from apps.scheduler.tasks.audio import generate_audio_scheduled; generate_audio_scheduled()"

publish:
	$(DC) exec web python manage.py shell -c \
		"from apps.scheduler.tasks.publish import publish_episode_scheduled; publish_episode_scheduled()"

publish-supabase:
	$(DC) exec web python manage.py publish_supabase

# ── Auth tokens ────────────────────────────────────────────────────────────────

youtube-token:
	python scripts/get_youtube_token.py \
		--client-id $(shell grep YOUTUBE_CLIENT_ID .env | cut -d= -f2) \
		--client-secret $(shell grep YOUTUBE_CLIENT_SECRET .env | cut -d= -f2)

# ── Tests ──────────────────────────────────────────────────────────────────────

test:
	$(DC) exec web python -m pytest tests/ -v

test-fast:
	$(DC) exec web python -m pytest tests/ -v -x --tb=short
