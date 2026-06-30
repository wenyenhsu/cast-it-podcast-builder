# Deployment Guide

This document describes how to build, deploy, and operate the Cast It AI Podcast Generator in local, staging, and production environments.

---

## Overview

| Environment | Compose file | Settings module | Web server |
|-------------|--------------|-----------------|------------|
| Development | `docker-compose.yml` | `config.settings.development` | Django runserver |
| Staging | `docker-compose.staging.yml` | `config.settings.staging` | Gunicorn + Nginx |
| Production | `docker-compose.prod.yml` | `config.settings.production` | Gunicorn + Nginx |

All deployment configuration is environment-driven. Never commit real secrets.

---

## Prerequisites

- Docker 24+ and Docker Compose v2
- Git
- For local (non-Docker) development: Python 3.13+

---

## Local Development

```bash
cp .env.example .env
./scripts/start.sh
```

Or manually:

```bash
docker compose up --build -d
```

Verify:

```bash
curl http://localhost:8000/api/v1/health/live/
curl http://localhost:8000/api/v1/version/
```

Stop:

```bash
./scripts/stop.sh
```

---

## Staging Deployment

1. Copy and configure the staging environment file:

```bash
cp .env.staging.example .env.staging
# Edit secrets, hosts, and credentials
```

2. Validate configuration:

```bash
ENVIRONMENT=staging DJANGO_SETTINGS_MODULE=config.settings.staging \
  python manage.py validate_config
```

3. Start the staging stack:

```bash
docker compose -f docker-compose.staging.yml --env-file .env.staging up --build -d
```

4. Verify readiness:

```bash
curl http://localhost:8080/api/v1/health/ready/
curl http://localhost:8080/api/v1/version/
```

---

## Production Deployment

### 1. Prepare environment

```bash
cp .env.production.example .env.production
```

Set at minimum:

- `DJANGO_SECRET_KEY` — long random string
- `DJANGO_ALLOWED_HOSTS` — explicit hostnames
- `CSRF_TRUSTED_ORIGINS` — HTTPS origins
- `POSTGRES_PASSWORD` — strong database password
- `BUILD_GIT_COMMIT`, `BUILD_NUMBER`, `IMAGE_TAG` — release traceability

### 2. Build a versioned image

```bash
./scripts/build.sh
```

Or with explicit tags:

```bash
IMAGE_TAG=v1.0.0 BUILD_NUMBER=42 ./scripts/build.sh
```

### 3. Validate configuration

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production \
  run --rm web validate-config
```

### 4. Deploy

```bash
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

The web container will:

1. Wait for PostgreSQL and Redis
2. Validate environment configuration
3. Run database migrations
4. Collect static files
5. Start Gunicorn

Traffic is served through Nginx on port 80 (configurable via `NGINX_HTTP_PORT`).

### 5. Post-deploy verification

```bash
curl http://localhost/api/v1/health/live/
curl http://localhost/api/v1/health/ready/
curl http://localhost/api/v1/version/
```

---

## Release Workflow

Every production release should follow this sequence:

1. **Build** — `./scripts/build.sh` with traceable `IMAGE_TAG`
2. **Test** — `./scripts/test.sh` and `./scripts/lint.sh` in CI
3. **Package** — Docker image tagged with git commit and build number
4. **Deploy** — `docker compose -f docker-compose.prod.yml up -d`
5. **Verify** — health, readiness, and version endpoints
6. **Rollback** — redeploy the previous `IMAGE_TAG` if verification fails

### Rollback procedure

```bash
# Set the previous known-good image tag
export IMAGE_TAG=<previous-tag>
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
./scripts/migrate.sh   # only if the failed release ran new migrations
```

If a migration caused the failure, restore the database from backup before rollback.

---

## CI/CD Pipeline

GitHub Actions workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

Automated steps:

| Step | Description |
|------|-------------|
| Ruff | Lint check |
| Black | Format check |
| Mypy | Type checking |
| Pytest | Unit and integration tests |
| Docker build | Production image build verification |
| Release | Tagged image build on `main` |

---

## Environment Variables

| Variable | Required (prod) | Description |
|----------|-----------------|-------------|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated hostnames |
| `CSRF_TRUSTED_ORIGINS` | Yes | HTTPS trusted origins |
| `ENVIRONMENT` | Yes | `development`, `staging`, or `production` |
| `POSTGRES_*` | Yes | Database connection |
| `REDIS_URL` | Yes | Redis connection |
| `CELERY_BROKER_URL` | Yes | Celery broker |
| `APP_VERSION` | Recommended | Semantic version |
| `BUILD_GIT_COMMIT` | Recommended | Git commit hash |
| `BUILD_NUMBER` | Recommended | CI build number |
| `IMAGE_TAG` | Recommended | Docker image tag |
| `USE_S3_STORAGE` | Optional | Enable S3-backed media/static |
| `COLLECT_STATIC_ON_START` | Optional | Run collectstatic on container start |

See [`.env.example`](../.env.example), [`.env.staging.example`](../.env.staging.example), and [`.env.production.example`](../.env.production.example).

---

## Operational Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build.sh` | Build production Docker image |
| `scripts/start.sh` | Start local development stack |
| `scripts/stop.sh` | Stop Docker Compose stack |
| `scripts/migrate.sh` | Run database migrations |
| `scripts/collectstatic.sh` | Collect static files |
| `scripts/test.sh` | Run pytest |
| `scripts/lint.sh` | Run ruff and mypy |
| `scripts/format.sh` | Run black |
| `scripts/create-admin.sh` | Create Django superuser |
| `scripts/backup-db.sh` | Backup PostgreSQL |
| `scripts/verify-backup.sh` | Verify backup integrity |

---

## Health and Readiness

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/health/live/` | Liveness — process is running |
| `GET /api/v1/health/ready/` | Readiness — dependencies available |
| `GET /api/v1/health/components/` | Per-component health |
| `GET /api/v1/version/` | Build metadata |

Docker healthchecks use these endpoints for web, worker, beat, and Nginx services.

---

## Static, Media, and Artifacts

| Path | Purpose | Production handling |
|------|---------|---------------------|
| `/app/staticfiles/` | Collected static assets | Nginx volume or S3 |
| `/app/media/` | Uploaded and generated audio | Shared volume or S3 |
| `/app/feeds/` | RSS feed output | Shared volume or S3 |

Enable object storage for production:

```bash
USE_S3_STORAGE=true
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

---

## Backup and Recovery

### Database backup

```bash
./scripts/backup-db.sh
./scripts/verify-backup.sh ./backups/postgres/cast_it_<timestamp>.sql.gz
```

### Media backup

Media files live in the `media_prod` Docker volume. Back up with:

```bash
docker run --rm -v cast-it-podcast-builder_media_prod:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/media_$(date -u +%Y%m%d).tar.gz -C /data .
```

---

## Troubleshooting

### Web container exits during startup

```bash
docker compose logs web
docker compose run --rm web validate-config
```

Common causes: missing `DJANGO_SECRET_KEY`, invalid `DJANGO_ALLOWED_HOSTS`, database not ready.

### Migrations failed

```bash
docker compose run --rm web migrate
```

### Celery worker unhealthy

```bash
docker compose logs celery-worker
docker compose exec celery-worker celery -A config inspect ping
```

### Static files not served

Ensure `collectstatic` ran and the Nginx volume is shared with the web container:

```bash
docker compose exec web python manage.py collectstatic --noinput
```

---

## Security Checklist

- [ ] `DJANGO_DEBUG=False` in staging and production
- [ ] Strong `DJANGO_SECRET_KEY` and database password
- [ ] Explicit `DJANGO_ALLOWED_HOSTS` (no wildcard)
- [ ] HTTPS enabled with `SECURE_SSL_REDIRECT`
- [ ] Containers run as non-root user (`appuser`, UID 1000)
- [ ] Secrets injected via environment, not committed to git
- [ ] Regular database and media backups configured

---

## Kubernetes Notes

The production Docker image is Kubernetes-ready:

- Stateless web and worker containers
- External PostgreSQL and Redis
- Health endpoints for probes:
  - Liveness: `/api/v1/health/live/`
  - Readiness: `/api/v1/health/ready/`
- Version metadata: `/api/v1/version/`
- Configuration via environment variables and secrets
