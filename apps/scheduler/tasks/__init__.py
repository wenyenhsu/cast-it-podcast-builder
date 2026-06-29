"""Celery tasks for the scheduler app."""

from apps.scheduler.tasks import (  # noqa: F401
    audio,
    classify,
    import_news,
    monitoring,
    pipeline,
    planning,
    publish,
    script,
    summarize,
)
from apps.scheduler.tasks.registry import get_task_for_job_type

__all__ = ["get_task_for_job_type"]
