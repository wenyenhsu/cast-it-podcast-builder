"""Celery task observability signal handlers."""

from __future__ import annotations

import logging
import time
from typing import Any

from celery import signals

from infrastructure.observability.context import bind_context, set_job_id
from services.observability.logging_service import StructuredLogService
from services.observability.metrics_service import ApplicationMetricsService

logger = logging.getLogger(__name__)
_log_service = StructuredLogService()
_metrics = ApplicationMetricsService()
_task_start_times: dict[str, float] = {}


def _extract_job_id(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    if kwargs.get("job_id"):
        return str(kwargs["job_id"])
    if len(args) >= 2:
        return str(args[1])
    if args:
        return str(args[0])
    return ""


@signals.before_task_publish.connect  # type: ignore[untyped-decorator]
def on_task_publish(
    sender: str | None = None,
    headers: dict[str, Any] | None = None,
    body: Any = None,
    **kwargs: Any,
) -> None:
    del sender, body, kwargs
    if headers is None:
        return
    _log_service.info(
        "Celery task published",
        event="celery_task_published",
        task_name=headers.get("task", ""),
    )


@signals.task_prerun.connect  # type: ignore[untyped-decorator]
def on_task_prerun(
    sender: Any = None,
    task_id: str | None = None,
    task: Any = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
    **extra: Any,
) -> None:
    del sender, extra
    task_name = getattr(task, "name", "unknown")
    queue = getattr(getattr(task, "request", None), "delivery_info", {}).get(
        "routing_key", "default"
    )
    job_id = _extract_job_id(args or (), kwargs or {})
    bind_context()
    if job_id:
        set_job_id(job_id)
    if task_id:
        _task_start_times[task_id] = time.perf_counter()
    _log_service.info(
        "Celery task started",
        event="celery_task_started",
        task_name=task_name,
        task_id=task_id or "",
        queue_name=queue,
        job_id=job_id,
    )


@signals.task_postrun.connect  # type: ignore[untyped-decorator]
def on_task_postrun(
    sender: Any = None,
    task_id: str | None = None,
    task: Any = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
    retval: Any = None,
    state: str | None = None,
    **extra: Any,
) -> None:
    del sender, retval, extra
    task_name = getattr(task, "name", "unknown")
    queue = getattr(getattr(task, "request", None), "delivery_info", {}).get(
        "routing_key", "default"
    )
    job_id = _extract_job_id(args or (), kwargs or {})
    start = _task_start_times.pop(task_id or "", None)
    duration = (time.perf_counter() - start) if start else 0.0
    retry_count = getattr(getattr(task, "request", None), "retries", 0) or 0
    success = state != "FAILURE"
    _metrics.record_celery_task(
        task_name=task_name,
        queue=queue,
        success=success,
        duration_seconds=duration,
        retry_count=retry_count,
    )
    _log_service.info(
        "Celery task completed",
        event="celery_task_completed" if success else "celery_task_failed",
        task_name=task_name,
        task_id=task_id or "",
        queue_name=queue,
        job_id=job_id,
        duration_ms=round(duration * 1000, 2),
        retry_count=retry_count,
        success=success,
    )


@signals.task_failure.connect  # type: ignore[untyped-decorator]
def on_task_failure(
    sender: Any = None,
    task_id: str | None = None,
    exception: BaseException | None = None,
    args: tuple[Any, ...] | None = None,
    kwargs: dict[str, Any] | None = None,
    traceback: Any = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    task_name = getattr(sender, "name", "unknown")
    job_id = _extract_job_id(args or (), kwargs or {})
    _log_service.error(
        "Celery task failed",
        event="celery_task_failed",
        task_name=task_name,
        task_id=task_id or "",
        job_id=job_id,
        error=str(exception) if exception else "",
    )


@signals.task_retry.connect  # type: ignore[untyped-decorator]
def on_task_retry(
    sender: Any = None,
    request: Any = None,
    reason: Any = None,
    einfo: Any = None,
    **extra: Any,
) -> None:
    del einfo, extra
    task_name = getattr(sender, "name", "unknown")
    task_id = getattr(request, "id", "")
    retries = getattr(request, "retries", 0)
    _log_service.warning(
        "Celery task retrying",
        event="celery_task_retrying",
        task_name=task_name,
        task_id=task_id,
        retry_count=retries,
        reason=str(reason) if reason else "",
    )
