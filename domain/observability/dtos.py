"""Observability data transfer objects."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from domain.observability.enums import EventSeverity, HealthStatus, SpanStatus


@dataclass(frozen=True)
class RequestContext:
    """Correlation context propagated across request and async boundaries."""

    correlation_id: str
    request_id: str
    job_id: str = ""
    workflow_run_id: str = ""
    episode_id: str = ""


@dataclass(frozen=True)
class HealthCheckResult:
    """Result of a single component health probe."""

    component: str
    status: HealthStatus
    checked_at: datetime
    latency_ms: float
    error_message: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class HealthSummary:
    """Aggregated health report."""

    status: HealthStatus
    checked_at: datetime
    components: list[HealthCheckResult]
    healthy_count: int
    warning_count: int
    unhealthy_count: int
    unknown_count: int


@dataclass(frozen=True)
class MetricSample:
    """Single metric observation."""

    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: datetime | None = None


@dataclass
class TraceSpan:
    """Distributed trace span."""

    span_id: str
    trace_id: str
    name: str
    start_time: datetime
    end_time: datetime | None = None
    duration_ms: float | None = None
    status: SpanStatus = SpanStatus.OK
    attributes: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = ""
    request_id: str = ""
    job_id: str = ""
    workflow_run_id: str = ""
    episode_id: str = ""
    parent_span_id: str = ""


@dataclass(frozen=True)
class OperationalEventDTO:
    """Normalized operational event for visibility and troubleshooting."""

    event_type: str
    severity: EventSeverity
    source: str
    name: str
    message: str
    correlation_id: str = ""
    request_id: str = ""
    job_id: str = ""
    workflow_run_id: str = ""
    episode_id: str = ""
    provider: str = ""
    duration_ms: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    id: UUID | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class DashboardSummary:
    """Backend data for operational dashboards."""

    recent_errors: list[dict[str, Any]]
    slowest_providers: list[dict[str, Any]]
    failed_workflows: list[dict[str, Any]]
    failed_jobs: list[dict[str, Any]]
    top_endpoints_by_latency: list[dict[str, Any]]
    health_summary: dict[str, Any]
    throughput_summary: dict[str, Any]
    retry_summary: dict[str, Any]
