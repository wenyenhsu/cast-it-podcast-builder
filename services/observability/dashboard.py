"""Operational dashboard data aggregation."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.scheduler.models import Job, JobStatus
from apps.workflow.models import WorkflowRun
from domain.observability.enums import EventSeverity
from domain.workflow.enums import WorkflowStatus
from services.observability.events import OperationalEventService
from services.observability.health.check_service import HealthCheckService
from services.observability.metrics_service import ApplicationMetricsService
from services.observability.performance import PerformanceTracker


class ObservabilityDashboardService:
    """Provide backend data structures for operational dashboards."""

    def __init__(
        self,
        events: OperationalEventService | None = None,
        health: HealthCheckService | None = None,
        metrics: ApplicationMetricsService | None = None,
        performance: PerformanceTracker | None = None,
    ) -> None:
        self._events = events or OperationalEventService()
        self._health = health or HealthCheckService()
        self._metrics = metrics or ApplicationMetricsService()
        self._performance = performance or PerformanceTracker()

    def summary(self) -> dict[str, Any]:
        since = timezone.now() - timedelta(days=1)
        return {
            "recent_errors": self.recent_errors(limit=20),
            "slowest_providers": self.slowest_providers(limit=10),
            "failed_workflows": self.failed_workflows(limit=10),
            "failed_jobs": self.failed_jobs(limit=10),
            "top_endpoints_by_latency": self.top_endpoints_by_latency(limit=10),
            "health_summary": self._health.overall_status(),
            "throughput_summary": self.throughput_summary(since=since),
            "retry_summary": self.retry_summary(since=since),
        }

    def recent_errors(self, *, limit: int = 20) -> list[dict[str, Any]]:
        events = self._events.list_events(
            severity=EventSeverity.ERROR.value,
            limit=limit,
        )
        critical = self._events.list_events(
            severity=EventSeverity.CRITICAL.value,
            limit=limit,
        )
        combined = sorted(
            events + critical,
            key=lambda item: item.created_at or timezone.now(),
            reverse=True,
        )
        return [
            OperationalEventService.dto_to_dict(event)
            for event in combined[:limit]
        ]

    def slowest_providers(self, *, limit: int = 10) -> list[dict[str, Any]]:
        samples = [
            sample
            for sample in self._metrics.export()
            if sample["name"] == "provider_duration_seconds_observation"
        ]
        samples.sort(key=lambda item: item["value"], reverse=True)
        return samples[:limit]

    def failed_workflows(self, *, limit: int = 10) -> list[dict[str, Any]]:
        runs = (
            WorkflowRun.objects.filter(status=WorkflowStatus.FAILED)
            .order_by("-updated_at")[:limit]
        )
        return [
            {
                "id": str(run.id),
                "status": run.status,
                "progress": run.progress,
                "error_message": run.error_message,
                "retry_count": run.retry_count,
                "updated_at": run.updated_at.isoformat(),
            }
            for run in runs
        ]

    def failed_jobs(self, *, limit: int = 10) -> list[dict[str, Any]]:
        jobs = (
            Job.objects.filter(status=JobStatus.FAILED)
            .order_by("-updated_at")[:limit]
        )
        return [
            {
                "id": str(job.id),
                "job_type": job.job_type,
                "status": job.status,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
                "updated_at": job.updated_at.isoformat(),
            }
            for job in jobs
        ]

    def top_endpoints_by_latency(self, *, limit: int = 10) -> list[dict[str, Any]]:
        samples = [
            sample
            for sample in self._metrics.export()
            if sample["name"] == "http_request_duration_seconds_observation"
        ]
        samples.sort(key=lambda item: item["value"], reverse=True)
        return samples[:limit]

    def throughput_summary(self, *, since: Any) -> dict[str, Any]:
        del since
        return {
            "http_requests": self._count_metric("http_request_total"),
            "celery_tasks": self._count_metric("celery_task_total"),
            "jobs_succeeded": self._count_metric("job_success_total"),
            "jobs_failed": self._count_metric("job_failure_total"),
        }

    def retry_summary(self, *, since: Any) -> dict[str, Any]:
        del since
        return {
            "workflow_retries": self._count_metric("workflow_retry_total"),
            "failed_workflows": WorkflowRun.objects.filter(
                status=WorkflowStatus.FAILED
            ).count(),
            "failed_jobs": Job.objects.filter(status=JobStatus.FAILED).count(),
        }

    def _count_metric(self, name: str) -> float:
        total = 0.0
        for sample in self._metrics.export():
            if sample["name"] == name:
                total += sample["value"]
        return total
