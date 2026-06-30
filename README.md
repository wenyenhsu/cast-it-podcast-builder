# Cast It — AI Podcast Generator

Production-ready Django platform that automates the full podcast production pipeline: news ingestion, article intelligence, episode planning, script generation, audio synthesis, post-processing, and publishing.

Built with clean architecture — business logic stays in `services/`, orchestration in dedicated layers, and Django models/views remain thin.

---

## Features

| Area | Capabilities |
|------|-------------|
| **Ingestion** | RSS/news source import, article storage, tagging |
| **Intelligence** | Summarization, classification, clustering, ranking |
| **Episode Planning** | Automated episode creation from ranked articles |
| **Script Generation** | LLM-powered multi-segment scripts with validation |
| **Audio** | TTS (Chatterbox), voice profiles, FFmpeg pipeline |
| **Publishing** | RSS feed generation, YouTube adapter |
| **Jobs & Scheduling** | Celery tasks, beat schedules, retry sweep |
| **Knowledge Base (RAG)** | pgvector embeddings, chunking, retrieval |
| **Workflow Engine** | Versioned pipelines — trackable, retryable, resumable, cancelable |
| **Observability** | Structured JSON logging, metrics, tracing, health probes |
| **Operations** | Django Admin dashboard for pipeline monitoring |
| **Deployment** | Multi-stage Docker images, staging/prod Compose, CI/CD |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Runtime | Python 3.13+, Django 5+, Django REST Framework |
| Data | PostgreSQL 16 + pgvector, Redis |
| Tasks | Celery, Celery Beat (`django_celery_beat`) |
| AI / Media | Ollama (LLM + embeddings), Chatterbox (TTS), FFmpeg |
| Quality | pytest, ruff, black, mypy |
| Deploy | Docker, Docker Compose, Gunicorn, Nginx, GitHub Actions |

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.13+ | Required for local development |
| Docker & Docker Compose | v2+ | Recommended for full stack |
| PostgreSQL | 16 + pgvector | Provided via Docker image |
| Redis | 7+ | Provided via Docker |
| Ollama | — | Optional; needed for LLM/embeddings |
| Chatterbox | — | Optional; needed for TTS |
| FFmpeg | — | Required for audio pipeline (included in prod image) |

---

## Initial Setup

Follow these steps the first time you clone the repository.

### 1. Clone the repository

```bash
git clone https://github.com/your-org/cast-it-podcast-builder.git
cd cast-it-podcast-builder
```

### 2. Create environment file

```bash
cp .env.example .env
```

Edit `.env` and set at minimum:

```bash
DJANGO_SECRET_KEY=your-secret-key-here
POSTGRES_PASSWORD=cast_it          # or a strong password
OLLAMA_CHAT_MODEL=llama3.2         # must match a model pulled in Ollama
OLLAMA_EMBED_MODEL=nomic-embed-text
```

> Never commit `.env` files containing real secrets.

### 3. Start with Docker (recommended)

```bash
./scripts/start.sh
# or: docker compose up --build -d
```

This starts:

| Service | Port | Description |
|---------|------|-------------|
| `web` | 8000 | Django API server |
| `db` | 5432 | PostgreSQL with pgvector |
| `redis` | 6379 | Cache & Celery broker |
| `celery-worker` | — | Background job worker |
| `celery-beat` | — | Scheduled task runner |

Migrations run automatically on container start via `docker/entrypoint.sh`.

Verify the stack:

```bash
curl http://localhost:8000/api/v1/health/live/
curl http://localhost:8000/api/v1/health/ready/
curl http://localhost:8000/api/v1/version/
```

Stop the stack:

```bash
./scripts/stop.sh
```

### 4. Local development (without Docker for the app)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env

docker compose up -d db redis
python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

Start Celery in separate terminals:

```bash
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 5. Pull required AI models (Ollama)

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Ensure `OLLAMA_BASE_URL` in `.env` points to your Ollama instance (default: `http://localhost:11434`).

### 6. Verify installation

```bash
pytest
python manage.py validate_config --warn-only
open http://localhost:8000/api/v1/docs/
open http://localhost:8000/admin/
```

---

## Project Structure

```
cast-it-podcast-builder/
├── config/                  Django settings (dev, testing, staging, production)
├── apps/                    Django applications (models, admin)
│   ├── articles/            News articles and tags
│   ├── episodes/            Podcast episodes
│   ├── scripts/             Script segments
│   ├── audio/               Audio assets and pipeline runs
│   ├── publish/             Publishing jobs
│   ├── scheduler/           Background jobs
│   ├── providers/           News sources and health checks
│   ├── knowledge/           RAG knowledge base (pgvector)
│   ├── workflow/            Workflow definitions and runs
│   └── observability/       Operational events
├── services/                Business logic layer
├── domain/                  DTOs, enums, exceptions, state machines
├── infrastructure/          External adapters (Celery, LLM, TTS, deployment)
├── api/                     REST API (v1)
├── docker/                  Dockerfile, entrypoint, Nginx, Gunicorn config
├── scripts/                 Operational helper scripts
├── docs/                    Deployment and operations documentation
├── tests/                   Test suite (310+ tests)
├── docker-compose.yml           Local development
├── docker-compose.staging.yml   Staging (Gunicorn + Nginx)
└── docker-compose.prod.yml        Production deployment
```

---

## Pipeline Overview

The default workflow (`podcast_production` v1) orchestrates:

```
Knowledge Ingestion
       ↓
Article Processing (summarize → classify → rank)
       ↓
Episode Planning
       ↓
Script Generation
       ↓
Audio Generation
       ↓
Audio Pipeline (FFmpeg)
       ↓
Publishing
```

Each step is trackable, retryable, resumable, and cancelable via the workflow engine.

---

## API Endpoints

Base URL: `http://localhost:8000/api/v1/`

### Core Resources

| Resource | Path |
|----------|------|
| Articles | `/articles/` |
| Episodes | `/episodes/` |
| Scripts | `/scripts/` |
| Audio Assets | `/audio-assets/` |
| Jobs | `/jobs/` |
| News Sources | `/news-sources/` |

Long-running actions (plan, generate-script, generate-audio, publish) return **202 Accepted** with a job reference.

### Health, Observability & Version

| Endpoint | Description |
|----------|-------------|
| `GET /health/` | Overall platform health |
| `GET /health/live/` | Liveness probe |
| `GET /health/ready/` | Readiness probe |
| `GET /health/components/` | Per-component health |
| `GET /metrics/` | Application metrics (JSON or `?format=prometheus`) |
| `GET /metrics/summary/` | Metrics dashboard summary |
| `GET /metrics/jobs/` | Job execution metrics |
| `GET /metrics/workflows/` | Workflow execution metrics |
| `GET /logs/` | Operational event logs |
| `GET /traces/` | Distributed trace spans |
| `GET /version/` | Build metadata (commit, tag, environment) |

Interactive API docs: `/api/v1/docs/` (Swagger) · `/api/v1/redoc/` (ReDoc)

---

## Development Commands

```bash
# Helper scripts (from repo root)
./scripts/test.sh
./scripts/lint.sh
./scripts/format.sh
./scripts/migrate.sh
./scripts/collectstatic.sh
./scripts/create-admin.sh

# Or run tools directly
pytest
ruff check .
black .
mypy .

# Database
python manage.py makemigrations
python manage.py migrate

# Validate deployment configuration
python manage.py validate_config
python manage.py validate_config --warn-only
```

### Running tests with pgvector

Tests require PostgreSQL with the pgvector extension:

```bash
docker compose up -d db
pytest
# or with a custom port:
POSTGRES_PORT=5435 pytest
```

---

## Environment Variables

Configuration is fully environment-driven. Example files:

| File | Purpose |
|------|---------|
| [`.env.example`](.env.example) | Local development |
| [`.env.staging.example`](.env.staging.example) | Staging deployment |
| [`.env.production.example`](.env.production.example) | Production deployment |

| Group | Key variables |
|-------|--------------|
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` |
| Redis / Celery | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| LLM | `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL` |
| RAG | `RAG_TOP_K`, `RAG_CHUNK_SIZE`, `RAG_EMBEDDING_DIMENSIONS` |
| TTS | `TTS_PROVIDER`, `CHATTERBOX_BASE_URL` |
| Audio | `FFMPEG_BINARY`, `AUDIO_TARGET_LUFS` |
| Publishing | `ENABLE_RSS_PUBLISHING`, `ENABLE_YOUTUBE_PUBLISHING`, `RSS_FEED_*` |
| Observability | `LOG_LEVEL`, `LOG_FORMAT`, `ENABLE_METRICS`, `ENABLE_TRACING` |
| Deployment | `APP_VERSION`, `BUILD_GIT_COMMIT`, `IMAGE_TAG`, `USE_S3_STORAGE` |
| Beat schedules | `BEAT_IMPORT_NEWS_CRON`, `BEAT_GENERATE_SCRIPT_CRON`, etc. |

---

## Deployment

Full guide: **[docs/deployment.md](docs/deployment.md)**

### Environments

| Environment | Compose file | Settings module | Web server |
|-------------|--------------|-----------------|------------|
| Development | `docker-compose.yml` | `config.settings.development` | Django runserver |
| Staging | `docker-compose.staging.yml` | `config.settings.staging` | Gunicorn + Nginx |
| Production | `docker-compose.prod.yml` | `config.settings.production` | Gunicorn + Nginx |

### Staging

```bash
cp .env.staging.example .env.staging
# edit secrets and hosts
docker compose -f docker-compose.staging.yml --env-file .env.staging up --build -d
curl http://localhost:8080/api/v1/health/ready/
```

### Production

```bash
cp .env.production.example .env.production
# edit secrets, hosts, and credentials
./scripts/build.sh
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
curl http://localhost/api/v1/health/ready/
curl http://localhost/api/v1/version/
```

### Operational scripts

| Script | Purpose |
|--------|---------|
| `scripts/build.sh` | Build versioned production Docker image |
| `scripts/start.sh` | Start local development stack |
| `scripts/stop.sh` | Stop Docker Compose services |
| `scripts/migrate.sh` | Run database migrations |
| `scripts/collectstatic.sh` | Collect static files |
| `scripts/backup-db.sh` | Backup PostgreSQL |
| `scripts/verify-backup.sh` | Verify backup file integrity |

### Rollback

Redeploy the previous known-good image tag:

```bash
export IMAGE_TAG=<previous-tag>
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
```

---

## CI/CD

GitHub Actions workflow: [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

| Step | Tool |
|------|------|
| Lint | ruff |
| Format check | black |
| Type check | mypy |
| Tests | pytest (with PostgreSQL + Redis services) |
| Docker build | Production image verification |
| Release | Tagged image build on `main` push |

---

## Architecture Principles

- **Clean architecture** — orchestration is separate from business services
- **Dependency injection** — services accept adapters via constructor/protocol
- **Adapter pattern** — external providers (LLM, TTS, publishers) are swappable
- **Job-based async** — long operations dispatch Celery jobs; API returns 202
- **Workflow engine** — explicit state machine for pipeline steps
- **Observability as cross-cutting concern** — logging, metrics, and tracing stay out of business logic
- **Environment-based config** — no hardcoded secrets, URLs, or credentials

---

## External Services

| Service | Default URL | Purpose |
|---------|-------------|---------|
| Ollama | `http://localhost:11434` | LLM chat + embeddings |
| Chatterbox | `http://localhost:8004` | Text-to-speech |
| FFmpeg | system PATH | Audio post-processing |

Health checks for all external services are available under `/api/v1/health/`.

---

## License

Private / internal use. Update this section when a license is chosen.
