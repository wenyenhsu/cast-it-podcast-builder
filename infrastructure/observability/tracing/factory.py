"""Tracing backend factory."""

from __future__ import annotations

from domain.observability.exceptions import MonitoringConfigurationError
from infrastructure.observability.tracing.base import TracingBackend
from infrastructure.observability.tracing.memory import InMemoryTracingBackend
from infrastructure.observability.tracing.noop import NoOpTracingBackend

_shared_backend: TracingBackend | None = None


def build_tracing_backend(backend_name: str, *, enabled: bool = True) -> TracingBackend:
    """Create a tracing backend from configuration."""
    if not enabled:
        return NoOpTracingBackend()
    normalized = backend_name.strip().lower()
    if normalized in {"memory", "in_memory", "test"}:
        return InMemoryTracingBackend()
    if normalized in {"noop", "none", "disabled"}:
        return NoOpTracingBackend()
    if normalized in {"opentelemetry", "otel"}:
        return InMemoryTracingBackend()
    raise MonitoringConfigurationError(
        f"Unsupported tracing backend: {backend_name!r}."
    )


def get_tracing_backend(
    backend_name: str | None = None,
    *,
    enabled: bool = True,
) -> TracingBackend:
    """Return a process-wide tracing backend singleton."""
    global _shared_backend
    if _shared_backend is None:
        name = backend_name or "memory"
        _shared_backend = build_tracing_backend(name, enabled=enabled)
    return _shared_backend


def reset_tracing_backend() -> None:
    """Reset the shared tracing backend (for tests)."""
    global _shared_backend
    if _shared_backend is not None:
        _shared_backend.reset()
    _shared_backend = None
