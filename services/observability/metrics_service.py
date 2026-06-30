"""Application metrics collection."""

from __future__ import annotations

import logging
from typing import Any

from domain.observability.exceptions import MetricsCollectionError
from infrastructure.observability.metrics.base import MetricsBackend
from infrastructure.observability.metrics.factory import get_metrics_backend
from services.observability.settings import ObservabilitySettings

logger = logging.getLogger(__name__)


class MetricNames:
    """Canonical metric names for the platform."""

    HTTP_REQUEST_COUNT = "http_request_total"
    HTTP_REQUEST_LATENCY = "http_request_duration_seconds"
    HTTP_ERROR_COUNT = "http_error_total"
    CELERY_TASK_COUNT = "celery_task_total"
    CELERY_TASK_LATENCY = "celery_task_duration_seconds"
    JOB_SUCCESS = "job_success_total"
    JOB_FAILURE = "job_failure_total"
    WORKFLOW_SUCCESS = "workflow_success_total"
    WORKFLOW_FAILURE = "workflow_failure_total"
    WORKFLOW_RETRY = "workflow_retry_total"
    PROVIDER_LATENCY = "provider_duration_seconds"
    PROVIDER_FAILURE = "provider_failure_total"
    SCRIPT_GENERATION_DURATION = "script_generation_duration_seconds"
    AUDIO_GENERATION_DURATION = "audio_generation_duration_seconds"
    AUDIO_PIPELINE_DURATION = "audio_pipeline_duration_seconds"
    PUBLISH_DURATION = "publish_duration_seconds"
    RSS_IMPORT_DURATION = "rss_import_duration_seconds"
    EMBEDDING_DURATION = "embedding_generation_duration_seconds"
    RETRIEVAL_LATENCY = "retrieval_latency_seconds"
    ARTICLES_IMPORTED_DAILY = "articles_imported_daily"
    EPISODES_PLANNED_DAILY = "episodes_planned_daily"
    SCRIPTS_GENERATED_DAILY = "scripts_generated_daily"
    AUDIO_GENERATED_DAILY = "audio_generated_daily"
    EPISODES_PUBLISHED_DAILY = "episodes_published_daily"
    FAILED_JOBS_DAILY = "failed_jobs_daily"
    FAILED_WORKFLOWS_DAILY = "failed_workflows_daily"


class ApplicationMetricsService:
    """Records platform metrics through a pluggable backend."""

    def __init__(
        self,
        backend: MetricsBackend | None = None,
        settings: ObservabilitySettings | None = None,
    ) -> None:
        self._settings = settings or ObservabilitySettings.from_django_settings()
        self._backend = backend or get_metrics_backend(self._settings.metrics_backend)

    @property
    def enabled(self) -> bool:
        return self._settings.enable_metrics

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            self._backend.increment(name, value=value, labels=labels)
        except Exception as exc:
            logger.warning(
                "Metric increment failed",
                extra={"event": "metrics_collection_error", "metric": name},
            )
            raise MetricsCollectionError(str(exc)) from exc

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        if not self.enabled:
            return
        try:
            self._backend.observe(name, value, labels=labels)
        except Exception as exc:
            logger.warning(
                "Metric observation failed",
                extra={"event": "metrics_collection_error", "metric": name},
            )
            raise MetricsCollectionError(str(exc)) from exc

    def record_http_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        labels = {"method": method, "path": path, "status": str(status_code)}
        self.increment(MetricNames.HTTP_REQUEST_COUNT, labels=labels)
        self.observe(MetricNames.HTTP_REQUEST_LATENCY, duration_seconds, labels=labels)
        if status_code >= 400:
            self.increment(MetricNames.HTTP_ERROR_COUNT, labels=labels)

    def record_celery_task(
        self,
        *,
        task_name: str,
        queue: str,
        success: bool,
        duration_seconds: float,
        retry_count: int = 0,
    ) -> None:
        labels = {
            "task": task_name,
            "queue": queue,
            "success": str(success).lower(),
        }
        self.increment(MetricNames.CELERY_TASK_COUNT, labels=labels)
        self.observe(MetricNames.CELERY_TASK_LATENCY, duration_seconds, labels=labels)
        if success:
            self.increment(MetricNames.JOB_SUCCESS, labels={"task": task_name})
        else:
            self.increment(MetricNames.JOB_FAILURE, labels={"task": task_name})
        if retry_count:
            self.increment(
                MetricNames.WORKFLOW_RETRY,
                value=float(retry_count),
                labels={"task": task_name},
            )

    def record_provider_call(
        self,
        *,
        provider: str,
        success: bool,
        duration_seconds: float,
    ) -> None:
        labels = {"provider": provider, "success": str(success).lower()}
        self.observe(MetricNames.PROVIDER_LATENCY, duration_seconds, labels=labels)
        if not success:
            self.increment(MetricNames.PROVIDER_FAILURE, labels={"provider": provider})

    def export(self) -> list[dict[str, Any]]:
        return [
            {
                "name": sample.name,
                "value": sample.value,
                "labels": sample.labels,
                "timestamp": (
                    sample.timestamp.isoformat() if sample.timestamp else None
                ),
            }
            for sample in self._backend.export()
        ]

    def export_prometheus(self) -> str:
        return self._backend.export_prometheus()

    def summary(self) -> dict[str, Any]:
        samples = self._backend.export()
        return {
            "sample_count": len(samples),
            "metrics": self.export(),
        }

    def jobs_summary(self) -> dict[str, Any]:
        samples = [
            sample
            for sample in self._backend.export()
            if sample.name.startswith("job_") or sample.name.startswith("celery_")
        ]
        metrics = [self._sample_dict(sample) for sample in samples]
        return {"count": len(samples), "metrics": metrics}

    def workflows_summary(self) -> dict[str, Any]:
        samples = [
            sample
            for sample in self._backend.export()
            if sample.name.startswith("workflow_")
        ]
        metrics = [self._sample_dict(sample) for sample in samples]
        return {"count": len(samples), "metrics": metrics}

    def providers_summary(self) -> dict[str, Any]:
        samples = [
            sample
            for sample in self._backend.export()
            if "provider" in sample.name
        ]
        metrics = [self._sample_dict(sample) for sample in samples]
        return {"count": len(samples), "metrics": metrics}

    @staticmethod
    def _sample_dict(sample: Any) -> dict[str, Any]:
        return {
            "name": sample.name,
            "value": sample.value,
            "labels": sample.labels,
        }
