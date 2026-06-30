"""Observability domain exceptions."""


class ObservabilityError(Exception):
    """Base class for observability failures."""


class MetricsCollectionError(ObservabilityError):
    """Raised when metric recording fails."""


class TracingError(ObservabilityError):
    """Raised when trace span operations fail."""


class HealthCheckError(ObservabilityError):
    """Raised when a health check cannot be executed."""


class LogCorrelationError(ObservabilityError):
    """Raised when log correlation context is invalid."""


class MonitoringConfigurationError(ObservabilityError):
    """Raised when observability configuration is invalid."""
