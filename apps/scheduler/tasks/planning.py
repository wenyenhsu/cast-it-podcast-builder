"""Episode planning Celery tasks."""

from celery import shared_task

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import (
    create_scheduled_job,
    job_task,
    run_registered_handler,
)
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_LLM


@job_task(
    name="scheduler.tasks.planning.episode_planning_task",
    job_type=JobType.EPISODE_PLANNING,
    queue=QUEUE_LLM,
)
def episode_planning_task(job_id: str) -> dict[str, object]:
    """Execute an episode planning job."""
    return run_registered_handler(JobType.EPISODE_PLANNING, job_id)


register_task(JobType.EPISODE_PLANNING, episode_planning_task)


@shared_task(name="scheduler.tasks.planning.episode_planning_scheduled")  # type: ignore[untyped-decorator]
def episode_planning_scheduled() -> str:
    """Beat entrypoint for daily episode planning."""
    return create_scheduled_job(JobType.EPISODE_PLANNING, payload={})
