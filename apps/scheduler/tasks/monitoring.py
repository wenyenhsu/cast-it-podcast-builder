"""Monitoring and maintenance Celery tasks."""

from celery import shared_task

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import (
    create_scheduled_job,
    job_task,
    run_registered_handler,
)
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_MONITORING


@job_task(
    name="scheduler.tasks.monitoring.retry_failed_jobs_task",
    job_type=JobType.RETRY_JOB,
    queue=QUEUE_MONITORING,
)
def retry_failed_jobs_task(job_id: str) -> dict[str, object]:
    """Execute a failed job retry sweep."""
    return run_registered_handler(JobType.RETRY_JOB, job_id)


register_task(JobType.RETRY_JOB, retry_failed_jobs_task)


@job_task(
    name="scheduler.tasks.monitoring.provider_health_check_task",
    job_type=JobType.HEALTH_CHECK,
    queue=QUEUE_MONITORING,
)
def provider_health_check_task(job_id: str) -> dict[str, object]:
    """Execute a provider health check job."""
    return run_registered_handler(JobType.HEALTH_CHECK, job_id)


register_task(JobType.HEALTH_CHECK, provider_health_check_task)


@shared_task(name="scheduler.tasks.monitoring.retry_failed_jobs_scheduled")  # type: ignore[untyped-decorator]
def retry_failed_jobs_scheduled() -> str:
    """Beat entrypoint for retry sweep."""
    return create_scheduled_job(JobType.RETRY_JOB, payload={"scheduled": True})


@shared_task(name="scheduler.tasks.monitoring.provider_health_check_scheduled")  # type: ignore[untyped-decorator]
def provider_health_check_scheduled() -> str:
    """Beat entrypoint for provider health checks."""
    return create_scheduled_job(JobType.HEALTH_CHECK, payload={"scheduled": True})
