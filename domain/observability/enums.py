"""Observability domain enumerations."""

from enum import StrEnum


class HealthStatus(StrEnum):
    """Normalized health state for monitored components."""

    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class EventSeverity(StrEnum):
    """Severity levels for operational events."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class SpanStatus(StrEnum):
    """Distributed tracing span status."""

    OK = "ok"
    ERROR = "error"
    CANCELLED = "cancelled"
