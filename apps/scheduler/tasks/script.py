"""Script generation Celery tasks."""

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import (
    job_task,
    run_registered_handler,
)
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_LLM


@job_task(
    name="scheduler.tasks.script.generate_script_task",
    job_type=JobType.GENERATE_SCRIPT,
    queue=QUEUE_LLM,
)
def generate_script_task(job_id: str) -> dict[str, object]:
    """Execute a script generation job."""
    return run_registered_handler(JobType.GENERATE_SCRIPT, job_id)


register_task(JobType.GENERATE_SCRIPT, generate_script_task)
