"""Celery task registry."""

from typing import Any

_TASK_REGISTRY: dict[str, Any] = {}


def register_task(job_type: str, task: Any) -> None:
    """Register a Celery task for a job type."""
    _TASK_REGISTRY[job_type] = task


def get_task_for_job_type(job_type: str) -> Any | None:
    """Return the Celery task registered for a job type."""
    return _TASK_REGISTRY.get(job_type)


def all_registered_tasks() -> dict[str, Any]:
    """Return all registered tasks."""
    return dict(_TASK_REGISTRY)
