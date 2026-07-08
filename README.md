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
| **Operations** | Standalone dashboard for pipeline monitoring (separate from Django Admin) |
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
OLLAMA_CHAT_MODEL=gemma3:12b       # must match a model pulled in Ollama
OLLAMA_EMBED_MODEL=nomic-embed-text
```

> Never commit `.env` files containing real secrets.

### 3. Start with Docker (recommended)

```bash
./scripts/start.sh
```

On success, the script prints the URLs for your stack, for example:

```
Cast It is running.

  API base:   http://localhost:32768/api/v1/
  Health:     http://localhost:32768/api/v1/health/live/
  API docs:   http://localhost:32768/api/v1/docs/
  Dashboard:  http://localhost:32768/
  Admin:      http://localhost:32768/admin/
  Version:    http://localhost:32768/api/v1/version/

Web port on host: 32768
```

Stop the stack:

```bash
./scripts/stop.sh
```

#### Docker services (local)

| Service | Host port | Description |
|---------|-----------|-------------|
| `web` | dynamic or fixed (see below) | Django API server |
| `db` | internal only | PostgreSQL with pgvector |
| `redis` | internal only | Cache & Celery broker |
| `celery-worker` | — | Background job worker |
| `celery-beat` | — | Scheduled task runner |

`db` and `redis` are **not** published to the host by default. This avoids conflicts when PostgreSQL (5432) or Redis (6379) are already running locally. Containers communicate over the internal Docker network.

Migrations run automatically on container start via `docker/entrypoint.sh`.

#### Port configuration

| Variable | Value | Behavior |
|----------|-------|----------|
| `WEB_PORT` | `0` or unset | Random host port (default) |
| `WEB_PORT` | `8000` | Fixed host port |

Add to `.env`:

```bash
WEB_PORT=0      # dynamic port — recommended when 8000 may be in use
# WEB_PORT=8000 # fixed port
```

To look up the current web port after starting:

```bash
docker compose port web 8000
```

### 4. Create staff login (Operations Dashboard)

The **Operations Dashboard** at `/` and **Django Admin** at `/admin/` share the same user accounts but are separate interfaces. Create a staff account after the stack is running:

**Docker (recommended):**

```bash
docker compose exec web python manage.py createsuperuser
```

Or use the helper script:

```bash
USE_DOCKER=true ./scripts/create-admin.sh
```

Follow the prompts for **Username**, **Email** (optional), and **Password** (typed twice; characters are hidden).

**Local Django (without Docker for web):**

```bash
python manage.py createsuperuser
```

Then open the URLs printed by `./scripts/start.sh`, for example:

```
http://localhost:32768/          # Operations Dashboard
http://localhost:32768/admin/    # Django Admin (model CRUD)
http://localhost:32768/accounts/login/   # Shared login
```

| Account type | Access |
|--------------|--------|
| **Superuser** (`createsuperuser`) | Full Operations dashboard + Django Admin |
| **Administrator / Operator / Reviewer** | Role-based access via Admin groups |

**Reset a forgotten password:**

```bash
docker compose exec web python manage.py changepassword <username>
```

**Operations dashboard pages** (login at `/accounts/login/`):

| Path | Purpose |
|------|---------|
| `/` | Overview dashboard |
| `/content/` | Unified article table (RSS + Manual) with script source checkboxes |
| `/scripts/` | Generated script list (`?episode=<id>` to filter) |
| `/scripts/<script-id>/` | Script detail with dialogue segments |
| `/providers/` | LLM, TTS, and Information Resources (`?tab=sources&resource=rss\|manual`) |
| `/monitor/` | Health, metrics, and logs (tabbed) |
| `/pipeline/<episode-id>/` | Episode pipeline status |

Legacy paths `/health/`, `/metrics/`, and `/logs/` redirect to `/monitor/` with the matching tab.

### 5. Local development (without Docker for the app)

Run Django on the host while database and Redis stay in Docker:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements/dev.txt
cp .env.example .env

# Start db + redis with host ports for local tools
docker compose -f docker-compose.yml -f docker-compose.host-access.yml up -d db redis
export POSTGRES_PORT="$(docker compose port db 5432 | cut -d: -f2)"

python manage.py migrate
python manage.py createsuperuser   # optional
python manage.py runserver
```

Start Celery in separate terminals:

```bash
celery -A config worker --loglevel=info -Q ingestion,llm,tts,audio,publishing,monitoring,celery
celery -A config beat --loglevel=info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### 6. Pull required AI models (Ollama)

```bash
ollama pull gemma3:12b
ollama pull nomic-embed-text
```

Ensure `OLLAMA_BASE_URL` in `.env` points to your Ollama instance (default: `http://localhost:11434`).

### 7. Verify installation

```bash
pytest
python manage.py validate_config --warn-only
```

Open the API docs using the port from `./scripts/start.sh` or `docker compose port web 8000`.

---

## Docker Compose Files

| File | Purpose |
|------|---------|
| [`docker-compose.yml`](docker-compose.yml) | Local development stack |
| [`docker-compose.host-access.yml`](docker-compose.host-access.yml) | Optional override — expose `db` / `redis` on the host |
| [`docker-compose.staging.yml`](docker-compose.staging.yml) | Staging (Gunicorn + Nginx) |
| [`docker-compose.prod.yml`](docker-compose.prod.yml) | Production deployment |

### Expose database or Redis on the host

Useful for running `pytest` or `psql` from the host without port conflicts:

```bash
# Dynamic host ports (recommended)
docker compose -f docker-compose.yml -f docker-compose.host-access.yml up -d db

# Or fixed host ports
POSTGRES_HOST_PORT=5435 docker compose \
  -f docker-compose.yml -f docker-compose.host-access.yml up -d db
```

Resolve the assigned port:

```bash
docker compose port db 5432
export POSTGRES_PORT="$(docker compose port db 5432 | cut -d: -f2)"
pytest
```

---

## Project Structure

```
cast-it-podcast-builder/
├── config/                        Django settings (dev, testing, staging, production)
├── apps/                          Django applications (models, admin)
├── services/                      Business logic layer
├── domain/                        DTOs, enums, exceptions, state machines
├── infrastructure/                External adapters (Celery, LLM, TTS, deployment)
├── api/                           REST API (v1)
├── docker/                        Dockerfile, entrypoint, Nginx, Gunicorn config
├── scripts/                       Operational helper scripts
├── docs/                          Deployment documentation
├── tests/                         Test suite (310+ tests)
├── docker-compose.yml             Local development
├── docker-compose.host-access.yml Optional db/redis host ports
├── docker-compose.staging.yml     Staging
└── docker-compose.prod.yml        Production
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

## Article Tagging (Fixed Taxonomy)

Articles are labeled two ways during the intelligence pipeline:

- **Category** — one broad bucket per article (AI, Programming, Cloud, …) via `templates/prompts/classification.md`.
- **Tags** — **1 to 3 tags chosen from a fixed tech taxonomy** (`ALLOWED_TAGS` in `domain/intelligence/constants.py`: Algorithms, LLM, Claude Fable, Machine Learning, Data Science, Infrastructure, Networking, Security, Privacy, UI/UX, Web Development, Mobile, Cloud, DevOps, Databases, Programming Languages, Open Source, Hardware, Robotics, Startups).

Rules enforced by `services/intelligence/keyword_service.py`:

- The LLM must pick from the allowed list; anything else is dropped (`canonicalize_tags`).
- An article's tags are **replaced** on each extraction, capped at 3.
- RSS/source-provided tags are kept only when they match the taxonomy.

**Adding a new tag** is a one-line change: append it to `ALLOWED_TAGS`. The next
`publish_supabase` run upserts the full taxonomy into Supabase (`sync_taxonomy()`),
so the two sides never drift. Removed tags are kept in Supabase because published
episodes may still reference them.

---

## Listener Distribution (Supabase)

The listener frontend ([cast-it-frontend](https://github.com/shuseiyokoi/cast-it-frontend))
does not talk to this Django backend. Generation happens locally; finished episodes
are pushed to a Supabase project that serves the public app ("local factory, cloud shelf").

```
Local pipeline (this repo)                    Supabase                     Listener app
────────────────────────────                  ─────────────────────────    ─────────────────────
generate episode + final audio ──ㅤpublishㅤ─▶ episodes / episode_tags  ─▶  personalized feed
                                              storage: episode-audio   ─▶  audio streaming
                                              activity_events          ◀─  play / progress events
                                              profiles + auth               login / signup
```

```bash
make publish-supabase   # sync taxonomy + push all episodes with final audio
# or a single episode:
docker compose exec web python manage.py publish_supabase --episode-id <uuid>
```

What it does (`services/publish/supabase_publisher.py`):

1. Upserts the tag taxonomy into `tags`.
2. Uploads the final MP3 to the public `episode-audio` storage bucket.
3. Upserts the episode row (title, summary, duration, audio URL, category).
4. Replaces the episode's `episode_tags` with the top 3 taxonomy tags across its articles.

Schema lives in `supabase/migrations/` (apply with `supabase db push`). Interest-based
ranking is done in-database by `personal_feed(p_session_id)`: it scores each tag by the
caller's listening time (30s heartbeats, completes, plays from `activity_events`) and
orders episodes by the summed score of their tags — for logged-in users (`auth.uid()`)
and anonymous sessions alike.

Required env vars (see `.env.example`): `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
`SUPABASE_AUDIO_BUCKET`.

---

## End-to-End Usage

Two ways to run the pipeline:

| Mode | When to use |
|------|-------------|
| **Scheduled (automatic)** | Daily production — Celery Beat runs import → plan → script → audio → publish on cron |
| **Manual (API)** | First-time testing, debugging, or single-episode control |

Set `BASE` to your API URL (port from `./scripts/start.sh`):

```bash
BASE=http://localhost:<port>/api/v1
```

### Prerequisites for generation

- **Ollama** running with chat + embed models (`OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL`)
- **Chatterbox** running for TTS (or configured TTS provider)
- **News source** configured (RSS URL)
- **Celery worker** running (`celery-worker` container or local worker)

### Manual pipeline (step by step)

Long-running API actions return **202 Accepted** with a `job_id`. Poll `GET /jobs/{job_id}/` until `status` is `succeeded`.

| Step | Action | API |
|------|--------|-----|
| 0 | Check health | `GET /health/live/`, `GET /health/llm/`, `GET /health/tts/` |
| 1 | Create news source | `POST /news-sources/` |
| 2 | Import articles | `POST /articles/import/` with `{"source_id": "..."}` |
| 3 | Create episode | `POST /episodes/` |
| 4 | Plan episode | `POST /episodes/{id}/plan/` |
| 5 | Generate script | `POST /episodes/{id}/generate-script/` |
| 6 | Generate audio | `POST /episodes/{id}/generate-audio/` |
| 7 | Publish | `POST /episodes/{id}/publish/` with `{"platforms": ["rss"]}` |

**Example — import articles:**

```bash
curl -X POST $BASE/articles/import/ \
  -H "Content-Type: application/json" \
  -d '{"source_id": "YOUR_SOURCE_UUID"}'
```

**Example — plan and generate:**

```bash
curl -X POST $BASE/episodes/EPISODE_UUID/plan/
curl -X POST $BASE/episodes/EPISODE_UUID/generate-script/
curl -X POST $BASE/episodes/EPISODE_UUID/generate-audio/
curl -X POST $BASE/episodes/EPISODE_UUID/publish/ \
  -H "Content-Type: application/json" \
  -d '{"platforms": ["rss"]}'
```

**Monitor jobs:**

```bash
curl $BASE/jobs/JOB_UUID/
curl -X POST $BASE/jobs/JOB_UUID/retry/    # on failure
curl -X POST $BASE/jobs/JOB_UUID/cancel/   # cancel running job
```

Use **Swagger UI** at `/api/v1/docs/` for interactive testing, or manage records in **Admin** at `/admin/`.

### Scheduled (automatic) pipeline

With `celery-beat` running, default cron jobs (configurable via `BEAT_*_CRON` in `.env`):

| Default time | Job |
|--------------|-----|
| 06:00 | Import news |
| 07:00 | Episode planning |
| — | Script generation (manual from `/content/`) |
| 09:00 | Audio generation |
| 10:00 | Publish episode |

Requires at least one enabled **news source** and healthy external services (Ollama, Chatterbox).

### Recommended first run

1. `./scripts/start.sh` — note the printed URLs  
2. `createsuperuser` — log in at `/accounts/login/` (Dashboard at `/`, Admin at `/admin/`)  
3. Create a **News Source** with a valid RSS URL  
4. `POST /articles/import/` — wait for job success  
5. `POST /episodes/` — create an episode  
6. Run `plan` → `generate-script` → `generate-audio` → `publish` in order  
7. Check `docker compose logs -f celery-worker` if jobs stay pending  

---

## API Endpoints

Base URL: `http://localhost:<port>/api/v1/` — use the port printed by `./scripts/start.sh`.

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
# Stack lifecycle
./scripts/start.sh          # start dev stack, print URLs
./scripts/stop.sh           # stop dev stack

# Quality & database
./scripts/test.sh
./scripts/lint.sh
./scripts/format.sh
./scripts/migrate.sh
./scripts/collectstatic.sh
USE_DOCKER=true ./scripts/create-admin.sh   # create Admin login (Docker)

# Or run tools directly
pytest
ruff check .
black .
mypy .
python manage.py makemigrations
python manage.py migrate
python manage.py validate_config --warn-only
```

### Running tests with pgvector

```bash
docker compose -f docker-compose.yml -f docker-compose.host-access.yml up -d db
export POSTGRES_PORT="$(docker compose port db 5432 | cut -d: -f2)"
pytest
```

---

## Troubleshooting

### Port already allocated

If you see `Bind for 0.0.0.0:6379 failed: port is already allocated`:

- Use `./scripts/start.sh` with the default `WEB_PORT=0` — `db` and `redis` are no longer bound to the host.
- For a fixed web port, ensure `WEB_PORT=8000` is free, or keep `WEB_PORT=0`.

### Cannot reach the API

```bash
docker compose ps
docker compose logs -f web
docker compose port web 8000
```

### Web container keeps restarting

```bash
docker compose logs web
docker compose exec web python manage.py migrate
```

### Cannot log in to Admin

No default account exists. Create one:

```bash
docker compose exec web python manage.py createsuperuser
```

Reset password:

```bash
docker compose exec web python manage.py changepassword <username>
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
| Docker (local) | `WEB_PORT`, `POSTGRES_HOST_PORT`, `REDIS_HOST_PORT` |
| Database | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` |
| Redis / Celery | `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` |
| LLM | `LLM_PROVIDER`, `OLLAMA_BASE_URL`, `OLLAMA_CHAT_MODEL`, `OLLAMA_EMBED_MODEL` |
| RAG | `RAG_TOP_K`, `RAG_CHUNK_SIZE`, `RAG_EMBEDDING_DIMENSIONS` |
| TTS | `TTS_PROVIDER`, `CHATTERBOX_BASE_URL` |
| Audio | `FFMPEG_BINARY`, `AUDIO_TARGET_LUFS` |
| Publishing | `ENABLE_RSS_PUBLISHING`, `ENABLE_YOUTUBE_PUBLISHING`, `RSS_FEED_*` |
| Observability | `LOG_LEVEL`, `LOG_FORMAT`, `ENABLE_METRICS`, `ENABLE_TRACING` |
| Deployment | `APP_VERSION`, `BUILD_GIT_COMMIT`, `IMAGE_TAG`, `USE_S3_STORAGE` |
| Beat schedules | `BEAT_IMPORT_NEWS_CRON`, `BEAT_GENERATE_AUDIO_CRON`, etc. (script is manual via `/content/`) |

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
docker compose -f docker-compose.staging.yml --env-file .env.staging up --build -d
curl http://localhost:8080/api/v1/health/ready/
```

### Production

```bash
cp .env.production.example .env.production
./scripts/build.sh
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
curl http://localhost/api/v1/health/ready/
curl http://localhost/api/v1/version/
```

### Operational scripts

| Script | Purpose |
|--------|---------|
| `scripts/build.sh` | Build versioned production Docker image |
| `scripts/start.sh` | Start dev stack and print access URLs |
| `scripts/stop.sh` | Stop Docker Compose services |
| `scripts/migrate.sh` | Run database migrations |
| `scripts/collectstatic.sh` | Collect static files |
| `scripts/backup-db.sh` | Backup PostgreSQL |
| `scripts/verify-backup.sh` | Verify backup file integrity |

### Rollback

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
