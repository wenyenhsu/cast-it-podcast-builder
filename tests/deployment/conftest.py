"""Deployment test fixtures."""

import pytest


@pytest.fixture
def production_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set minimal valid production environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "secure-production-secret-key")
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("POSTGRES_DB", "cast_it")
    monkeypatch.setenv("POSTGRES_USER", "cast_it")
    monkeypatch.setenv("POSTGRES_PASSWORD", "cast_it")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
