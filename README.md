# Cast It — AI Podcast Generator

Production-ready Django foundation for an AI-powered podcast generation platform.

## Tech Stack

- Python 3.13+
- Django 5+ with Django REST Framework
- PostgreSQL, Redis, Celery, Celery Beat
- Docker & Docker Compose
- pytest, ruff, black, mypy

## Project Structure

```
config/          Django project settings and Celery config
apps/            Django applications (core, users, articles, …)
services/        Business logic layer
domain/          Domain entities and interfaces
infrastructure/  External adapters and integrations
api/             REST API endpoints
tests/           Test suite
docker/          Docker configuration
```

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
docker compose up --build
```

The API health check is available at `http://localhost:8000/api/v1/health/`.

If local ports are already in use, adjust the `ports` mappings in `docker-compose.yml`.

### Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements/dev.txt
cp .env.example .env

# Start PostgreSQL and Redis (or use docker compose up db redis)
python manage.py migrate
python manage.py runserver
```

## Development Commands

```bash
# Run tests
pytest

# Lint and format
ruff check .
black .
mypy .

# Celery worker (local)
celery -A config worker --loglevel=info
```

## Environment Variables

See `.env.example` for all configuration options. Never commit `.env` files with real secrets.
