"""Metrics backend factory."""

from __future__ import annotations

from domain.observability.exceptions import MonitoringConfigurationError
from infrastructure.observability.metrics.base import MetricsBackend
from infrastructure.observability.metrics.memory import InMemoryMetricsBackend
from infrastructure.observability.metrics.prometheus import PrometheusMetricsBackend

_shared_backend: MetricsBackend | None = None


def build_metrics_backend(backend_name: str) -> MetricsBackend:
    """Create a metrics backend from configuration."""
    normalized = backend_name.strip().lower()
    if normalized in {"memory", "in_memory", "test"}:
        return InMemoryMetricsBackend()
    if normalized in {"prometheus", "prom"}:
        return PrometheusMetricsBackend()
    raise MonitoringConfigurationError(
        f"Unsupported metrics backend: {backend_name!r}."
    )


def get_metrics_backend(backend_name: str | None = None) -> MetricsBackend:
    """Return a process-wide metrics backend singleton."""
    global _shared_backend
    if _shared_backend is None:
        name = backend_name or "memory"
        _shared_backend = build_metrics_backend(name)
    return _shared_backend


def reset_metrics_backend() -> None:
    """Reset the shared metrics backend (for tests)."""
    global _shared_backend
    if _shared_backend is not None:
        _shared_backend.reset()
    _shared_backend = None
