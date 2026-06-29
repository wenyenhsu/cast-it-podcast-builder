"""Scheduled and on-demand news import tasks."""

from celery import shared_task

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import (
    create_scheduled_job,
    job_task,
    run_registered_handler,
)
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_INGESTION


@job_task(
    name="scheduler.tasks.import_news.import_news_task",
    job_type=JobType.IMPORT_NEWS,
    queue=QUEUE_INGESTION,
)
def import_news_task(job_id: str) -> dict[str, object]:
    """Execute a news import job."""
    return run_registered_handler(JobType.IMPORT_NEWS, job_id)


register_task(JobType.IMPORT_NEWS, import_news_task)


@shared_task(name="scheduler.tasks.import_news.import_news_scheduled")  # type: ignore[untyped-decorator]
def import_news_scheduled() -> str:
    """Beat entrypoint that creates and dispatches a news import job."""
    return create_scheduled_job(JobType.IMPORT_NEWS, payload={})
