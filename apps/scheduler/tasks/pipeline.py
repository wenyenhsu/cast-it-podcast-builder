"""Audio pipeline Celery tasks."""

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import job_task, run_registered_handler
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_AUDIO


@job_task(
    name="scheduler.tasks.pipeline.run_audio_pipeline_task",
    job_type=JobType.RUN_AUDIO_PIPELINE,
    queue=QUEUE_AUDIO,
)
def run_audio_pipeline_task(job_id: str) -> dict[str, object]:
    """Execute an audio pipeline job."""
    return run_registered_handler(JobType.RUN_AUDIO_PIPELINE, job_id)


register_task(JobType.RUN_AUDIO_PIPELINE, run_audio_pipeline_task)
