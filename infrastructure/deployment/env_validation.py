"""Environment configuration validation for deployment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from infrastructure.deployment.exceptions import DeploymentConfigurationError


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of an environment validation run."""

    environment: str
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


_INSECURE_SECRET_VALUES = frozenset(
    {
        "",
        "change-me-in-production",
        "change-me",
        "test-secret-key-not-for-production",
    }
)

_BASE_REQUIRED = (
    "DJANGO_SECRET_KEY",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_HOST",
    "REDIS_URL",
    "CELERY_BROKER_URL",
)

_PRODUCTION_REQUIRED = _BASE_REQUIRED + (
    "DJANGO_ALLOWED_HOSTS",
    "ENVIRONMENT",
)

_STAGING_REQUIRED = _PRODUCTION_REQUIRED


def validate_environment(
    *,
    environment: str | None = None,
    strict: bool = True,
) -> ValidationResult:
    """Validate required environment variables for the target environment."""
    env_name = (environment or os.getenv("ENVIRONMENT", "development")).lower()
    errors: list[str] = []
    warnings: list[str] = []

    if env_name in {"production", "staging"}:
        required = (
            _PRODUCTION_REQUIRED if env_name == "production" else _STAGING_REQUIRED
        )
        for key in required:
            value = os.getenv(key, "").strip()
            if not value:
                errors.append(f"Missing required environment variable: {key}")

        secret = os.getenv("DJANGO_SECRET_KEY", "").strip()
        if secret in _INSECURE_SECRET_VALUES:
            errors.append("DJANGO_SECRET_KEY must be set to a secure production value.")

        if os.getenv("DJANGO_DEBUG", "false").lower() in {"true", "1", "yes"}:
            errors.append("DJANGO_DEBUG must be false in production-like environments.")

        allowed_hosts = os.getenv("DJANGO_ALLOWED_HOSTS", "").strip()
        if allowed_hosts in {"", "*"}:
            errors.append("DJANGO_ALLOWED_HOSTS must list explicit hostnames.")

    elif env_name == "development":
        for key in ("DJANGO_SECRET_KEY", "POSTGRES_DB", "POSTGRES_HOST"):
            if not os.getenv(key, "").strip():
                warnings.append(f"Recommended variable not set: {key}")
    else:
        warnings.append(f"Unknown environment name: {env_name}")

    valid = not errors
    if strict and errors:
        raise DeploymentConfigurationError(
            f"Environment validation failed for '{env_name}': " + "; ".join(errors)
        )
    return ValidationResult(
        environment=env_name,
        valid=valid,
        errors=errors,
        warnings=warnings,
    )
