"""Publishing Celery tasks."""

from celery import shared_task

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import (
    create_scheduled_job,
    job_task,
    run_registered_handler,
)
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_PUBLISHING


@job_task(
    name="scheduler.tasks.publish.publish_episode_task",
    job_type=JobType.PUBLISH_EPISODE,
    queue=QUEUE_PUBLISHING,
)
def publish_episode_task(job_id: str) -> dict[str, object]:
    """Execute a publish episode job."""
    return run_registered_handler(JobType.PUBLISH_EPISODE, job_id)


register_task(JobType.PUBLISH_EPISODE, publish_episode_task)


@shared_task(name="scheduler.tasks.publish.publish_episode_scheduled")  # type: ignore[untyped-decorator]
def publish_episode_scheduled() -> str:
    """Beat entrypoint for daily publishing."""
    return create_scheduled_job(
        JobType.PUBLISH_EPISODE,
        payload={"scheduled": True},
    )


@shared_task(name="scheduler.tasks.publish.publish_supabase_scheduled")  # type: ignore[untyped-decorator]
def publish_supabase_scheduled() -> dict[str, int]:
    """Beat entrypoint that pushes ready episodes to Supabase for the listener app."""
    from services.publish.supabase_publisher import SupabasePublisher

    publisher = SupabasePublisher()
    publisher.sync_taxonomy()
    episodes = publisher.publishable_episodes()
    for episode in episodes:
        publisher.publish_episode(episode)
    return {"published": len(episodes)}
