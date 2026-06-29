"""Shared Celery task utilities."""

from collections.abc import Callable
from typing import Any

from celery import shared_task

from domain.jobs.exceptions import JobTransientError
from infrastructure.jobs.handlers import HANDLER_REGISTRY
from infrastructure.jobs.runner import JobTaskRunner
from services.jobs.settings import JobSettings


def job_task(
    *,
    name: str,
    job_type: str,
    queue: str,
) -> Callable[[Callable[..., Any]], Any]:
    """Decorator factory for standardized job Celery tasks."""
    settings = JobSettings.from_django_settings()

    def decorator(func: Callable[..., Any]) -> Any:
        @shared_task(  # type: ignore[untyped-decorator]
            bind=True,
            name=name,
            queue=queue,
            autoretry_for=(JobTransientError,),
            retry_backoff=True,
            retry_backoff_max=settings.retry_max_delay_seconds,
            max_retries=settings.task_max_retries,
            time_limit=settings.task_time_limit,
            soft_time_limit=settings.task_soft_time_limit,
        )
        def wrapper(self: object, job_id: str) -> dict[str, Any]:
            result: dict[str, Any] = func(job_id)
            return result

        return wrapper

    return decorator


def run_registered_handler(job_type: str, job_id: str) -> dict[str, Any]:
    """Execute a registered handler through the job task runner."""
    handler = HANDLER_REGISTRY[job_type]
    runner = JobTaskRunner()
    return runner.run_handler(job_id, handler)


def create_scheduled_job(job_type: str, payload: dict[str, Any] | None = None) -> str:
    """Create a job for scheduled beat tasks and return its id."""
    from apps.scheduler.tasks.registry import get_task_for_job_type
    from services.jobs.dispatch import JobDispatchService

    task = get_task_for_job_type(job_type)
    if task is None:
        raise ValueError(f"No task registered for job type: {job_type}")

    job = JobDispatchService().create_and_dispatch(
        job_type,
        task,
        payload=payload,
    )
    return str(job.id)
