# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Builder stage — compile dependencies and install Python packages
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --upgrade pip \
    && pip wheel --wheel-dir /wheels -r requirements/prod.txt

# ---------------------------------------------------------------------------
# Development image — includes dev dependencies and runs as root for bind mounts
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS development

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.development

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ requirements/
RUN pip install --upgrade pip \
    && pip install -r requirements/dev.txt

COPY . .
RUN chmod +x docker/entrypoint.sh docker/wait-for-services.sh

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live/ || exit 1

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["web"]

# ---------------------------------------------------------------------------
# Production runtime image — minimal, non-root
# ---------------------------------------------------------------------------
FROM python:3.13-slim AS production

ARG BUILD_GIT_COMMIT=unknown
ARG BUILD_NUMBER=local
ARG BUILD_TIMESTAMP
ARG APP_VERSION=0.1.0
ARG IMAGE_TAG=local

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    BUILD_GIT_COMMIT=${BUILD_GIT_COMMIT} \
    BUILD_NUMBER=${BUILD_NUMBER} \
    BUILD_TIMESTAMP=${BUILD_TIMESTAMP} \
    APP_VERSION=${APP_VERSION} \
    IMAGE_TAG=${IMAGE_TAG} \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --create-home appuser

COPY --from=builder /wheels /wheels
RUN python -m venv /opt/venv \
    && pip install --upgrade pip \
    && pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY --chown=appuser:appuser . .

RUN mkdir -p /app/staticfiles /app/media /app/feeds \
    && chown -R appuser:appuser /app/staticfiles /app/media /app/feeds \
    && chmod +x docker/entrypoint.sh docker/wait-for-services.sh

USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health/live/ || exit 1

ENTRYPOINT ["docker/entrypoint.sh"]
CMD ["gunicorn"]
