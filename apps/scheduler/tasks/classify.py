"""Article classification Celery tasks."""

from apps.scheduler.models import JobType
from apps.scheduler.tasks.base import job_task, run_registered_handler
from apps.scheduler.tasks.registry import register_task
from domain.jobs.queues import QUEUE_LLM


@job_task(
    name="scheduler.tasks.classify.classify_article_task",
    job_type=JobType.CLASSIFY_ARTICLE,
    queue=QUEUE_LLM,
)
def classify_article_task(job_id: str) -> dict[str, object]:
    """Execute an article classification job."""
    return run_registered_handler(JobType.CLASSIFY_ARTICLE, job_id)


register_task(JobType.CLASSIFY_ARTICLE, classify_article_task)
