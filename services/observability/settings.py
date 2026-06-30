"""Observability configuration."""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ObservabilitySettings:
    """Runtime observability configuration."""

    log_level: str
    log_format: str
    service_name: str
    environment: str
    enable_metrics: bool
    enable_tracing: bool
    enable_health_endpoints: bool
    request_id_header: str
    correlation_id_header: str
    metrics_backend: str
    tracing_backend: str

    @classmethod
    def from_django_settings(cls) -> ObservabilitySettings:
        return cls(
            log_level=getattr(settings, "OBSERVABILITY_LOG_LEVEL", "INFO"),
            log_format=getattr(settings, "OBSERVABILITY_LOG_FORMAT", "json"),
            service_name=getattr(settings, "OBSERVABILITY_SERVICE_NAME", "cast-it"),
            environment=getattr(settings, "OBSERVABILITY_ENVIRONMENT", "development"),
            enable_metrics=getattr(settings, "OBSERVABILITY_ENABLE_METRICS", True),
            enable_tracing=getattr(settings, "OBSERVABILITY_ENABLE_TRACING", True),
            enable_health_endpoints=getattr(
                settings, "OBSERVABILITY_ENABLE_HEALTH_ENDPOINTS", True
            ),
            request_id_header=getattr(
                settings, "OBSERVABILITY_REQUEST_ID_HEADER", "X-Request-ID"
            ),
            correlation_id_header=getattr(
                settings,
                "OBSERVABILITY_CORRELATION_ID_HEADER",
                "X-Correlation-ID",
            ),
            metrics_backend=getattr(
                settings, "OBSERVABILITY_METRICS_BACKEND", "memory"
            ),
            tracing_backend=getattr(
                settings, "OBSERVABILITY_TRACING_BACKEND", "memory"
            ),
        )
