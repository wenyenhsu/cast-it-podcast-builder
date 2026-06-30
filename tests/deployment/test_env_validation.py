"""Environment validation tests."""

import pytest

from infrastructure.deployment.env_validation import validate_environment
from infrastructure.deployment.exceptions import DeploymentConfigurationError


def test_development_validation_allows_missing_optional(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    result = validate_environment(environment="development", strict=False)
    assert result.environment == "development"
    assert result.valid is True


def test_production_validation_fails_without_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("DJANGO_SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")
    monkeypatch.setenv("POSTGRES_DB", "cast_it")
    monkeypatch.setenv("POSTGRES_USER", "cast_it")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_HOST", "db")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    with pytest.raises(DeploymentConfigurationError):
        validate_environment(environment="production", strict=True)


def test_production_validation_passes_with_valid_env(
    production_env: None,
) -> None:
    result = validate_environment(environment="production", strict=True)
    assert result.valid is True
    assert result.errors == []


def test_production_rejects_debug_enabled(
    production_env: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DJANGO_DEBUG", "true")
    with pytest.raises(DeploymentConfigurationError):
        validate_environment(environment="production", strict=True)
