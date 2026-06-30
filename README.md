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
| **Workflow Engine** | Versioned pipelines — trackable, retryable, resumable |
| **Observability** | Structured logging, metrics, tracing, health probes |
| **Operations** | Django Admin dashboard for pipeline monitoring |

---

## Tech Stack

- **Runtime:** Python 3.13+, Django 5+, Django REST Framework
- **Data:** PostgreSQL 16 + pgvector, Redis
- **Tasks:** Celery, Celery Beat (`django_celery_beat`)
- **AI / Media:** Ollama (LLM + embeddings), Chatterbox (TTS), FFmpeg
- **Quality:** pytest, ruff, black, mypy
- **Deploy:** Docker & Docker Compose

---

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.13+ | Required for local development |
| Docker & Docker Compose | Latest | Recommended for full stack |
| PostgreSQL | 16 + pgvector | Provided via Docker image |
| Redis | 7+ | Provided via Docker |
| Ollama | — | Optional; needed for LLM/embeddings |
| Chatterbox | — | Optional; needed for TTS |
| FFmpeg | — | Required for audio pipeline |

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

### 3. Start infrastructure (Docker — recommended)

```bash
docker compose up --build -d
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

Verify the stack is healthy:

```bash
curl http://localhost:8000/api/v1/health/
curl http://localhost:8000/api/v1/health/live/
curl http://localhost:8000/api/v1/health/ready/
```

Expected response (overall health):

```json
{
  "status": "ok",
  "checks": { ... }
}
```

### 4. Initial setup (local development)

If you prefer running Django locally without Docker for the app process:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements/dev.txt

# Copy environment file
cp .env.example .env

# Start only database and Redis via Docker
docker compose up -d db redis

# Run initial database migrations
python manage.py migrate

# (Optional) Create a superuser for Django Admin
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

In a separate terminal, start Celery:

```bash
source .venv/bin/activate
celery -A config worker --loglevel=info
```

And Celery Beat (for scheduled jobs):

```bash
source .venv/bin/activate
celery -A config beat --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 5. Pull required AI models (Ollama)

If using Ollama locally:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Ensure `OLLAMA_BASE_URL` in `.env` points to your Ollama instance (default: `http://localhost:11434`).

### 6. Verify installation

```bash
# Run the test suite
pytest

# Open API documentation
open http://localhost:8000/api/v1/docs/

# Open Django Admin (after createsuperuser)
open http://localhost:8000/admin/
```

---

## Project Structure

```
cast-it-podcast-builder/
├── config/              Django settings, Celery, WSGI/ASGI
├── apps/                Django applications (models, admin)
│   ├── articles/        News articles and tags
│   ├── episodes/        Podcast episodes
│   ├── scripts/         Script segments
│   ├── audio/           Audio assets and pipeline runs
│   ├── publish/         Publishing jobs
│   ├── scheduler/       Background jobs
│   ├── providers/       News sources and health checks
│   ├── knowledge/       RAG knowledge base (pgvector)
│   ├── workflow/        Workflow definitions and runs
│   └── observability/   Operational events
├── services/            Business logic layer
├── domain/              DTOs, enums, exceptions, state machines
├── infrastructure/      External adapters (Celery, LLM, TTS, vector store)
├── api/                 REST API (v1)
├── tests/               Test suite (~300 tests)
└── docker/              Dockerfile and entrypoint
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

### Health & Observability

| Endpoint | Description |
|----------|-------------|
| `GET /health/` | Overall platform health |
| `GET /health/live/` | Liveness probe |
| `GET /health/ready/` | Readiness probe |
| `GET /health/components/` | Per-component health |
| `GET /metrics/` | Application metrics (JSON or `?format=prometheus`) |
| `GET /metrics/summary/` | Metrics dashboard summary |
| `GET /logs/` | Operational event logs |
| `GET /traces/` | Distributed trace spans |

Interactive API docs: `/api/v1/docs/` (Swagger) · `/api/v1/redoc/` (ReDoc)

---

## Development Commands

```bash
# Run all tests
pytest

# Run a specific test module
pytest tests/observability/ -v

# Lint, format, type-check
ruff check .
black .
mypy .

# Create migrations after model changes
python manage.py makemigrations
python manage.py migrate

# Django shell
python manage.py shell
```

### Running tests with pgvector

Tests require a PostgreSQL instance with the pgvector extension:

```bash
docker compose up -d db
POSTGRES_PORT=5432 pytest
```

---

## Environment Variables

All configuration is driven by environment variables. See [`.env.example`](.env.example) for the full list.

| Group | Key variables |
|-------|--------------|
| Django | `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS` |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` |
| Redis / Celery | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| LLM | `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL` |
| RAG | `RAG_TOP_K`, `RAG_CHUNK_SIZE`, `RAG_EMBEDDING_DIMENSIONS` |
| TTS | `TTS_PROVIDER`, `CHATTERBOX_BASE_URL` |
| Audio | `FFMPEG_BINARY`, `AUDIO_TARGET_LUFS` |
| Publishing | `ENABLE_RSS_PUBLISHING`, `ENABLE_YOUTUBE_PUBLISHING`, `RSS_FEED_*` |
| Observability | `LOG_LEVEL`, `LOG_FORMAT`, `ENABLE_METRICS`, `ENABLE_TRACING`, `METRICS_BACKEND` |
| Beat schedules | `BEAT_IMPORT_NEWS_CRON`, `BEAT_GENERATE_SCRIPT_CRON`, etc. |

---

## Architecture Principles

- **Clean architecture** — orchestration is separate from business services
- **Dependency injection** — services accept adapters via constructor/protocol
- **Adapter pattern** — external providers (LLM, TTS, publishers) are swappable
- **Job-based async** — long operations dispatch Celery jobs, API returns 202
- **Observability as cross-cutting concern** — logging, metrics, and tracing never live inside business logic

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
