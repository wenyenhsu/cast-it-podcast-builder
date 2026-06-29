"""Segment audio generation Celery tasks."""

from celery import shared_task

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import (
    create_scheduled_job,
    job_task,
    run_registered_handler,
)
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_TTS


@job_task(
    name="scheduler.tasks.audio.generate_audio_task",
    job_type=JobType.GENERATE_AUDIO,
    queue=QUEUE_TTS,
)
def generate_audio_task(job_id: str) -> dict[str, object]:
    """Execute a segment audio generation job."""
    return run_registered_handler(JobType.GENERATE_AUDIO, job_id)


register_task(JobType.GENERATE_AUDIO, generate_audio_task)


@shared_task(name="scheduler.tasks.audio.generate_audio_scheduled")  # type: ignore[untyped-decorator]
def generate_audio_scheduled() -> str:
    """Beat entrypoint for daily audio generation."""
    return create_scheduled_job(
        JobType.GENERATE_AUDIO,
        payload={"scheduled": True},
    )
