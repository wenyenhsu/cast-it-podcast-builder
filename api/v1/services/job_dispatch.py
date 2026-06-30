"""Async job dispatch for API actions."""

from typing import Any

from api.v1.exceptions import ServiceUnavailableError
from apps.scheduler.models import Job, JobType
from apps.scheduler.tasks.registry import get_task_for_job_type
from services.jobs.dispatch import JobDispatchService


class ApiJobDispatchService:
    """Dispatches background jobs for API-triggered actions."""

    _JOB_MESSAGES: dict[str, str] = {
        JobType.IMPORT_NEWS: "News import has been queued.",
        JobType.SUMMARIZE_ARTICLE: "Article summarization has been queued.",
        JobType.CLASSIFY_ARTICLE: "Article classification has been queued.",
        JobType.EPISODE_PLANNING: "Episode planning has been queued.",
        JobType.GENERATE_SCRIPT: "Script generation has been queued.",
        JobType.GENERATE_AUDIO: "Audio generation has been queued.",
        JobType.RUN_AUDIO_PIPELINE: "Audio pipeline has been queued.",
        JobType.PUBLISH_EPISODE: "Episode publishing has been queued.",
        JobType.HEALTH_CHECK: "Health check has been queued.",
    }

    def __init__(self, dispatch_service: JobDispatchService | None = None) -> None:
        self._dispatch = dispatch_service or JobDispatchService()

    def dispatch(self, job_type: str, payload: dict[str, Any] | None = None) -> Job:
        """Create and enqueue a background job."""
        task = get_task_for_job_type(job_type)
        if task is None:
            raise ServiceUnavailableError(
                detail=f"No task registered for job type '{job_type}'."
            )
        return self._dispatch.create_and_dispatch(job_type, task, payload)

    def build_accepted_response(
        self,
        job: Job,
        *,
        job_type: str | None = None,
        detail: str | None = None,
    ) -> dict[str, str]:
        """Build a standardized 202 Accepted response body."""
        resolved_type = job_type or job.job_type
        message = detail or self._JOB_MESSAGES.get(
            resolved_type,
            "Background job has been queued.",
        )
        return {
            "job_id": str(job.id),
            "status": job.status,
            "detail": message,
            "status_url": f"/api/v1/jobs/{job.id}/",
        }

    def redispatch(self, job: Job) -> Job:
        """Re-enqueue an existing job after retry."""
        task = get_task_for_job_type(job.job_type)
        if task is None:
            raise ServiceUnavailableError(
                detail=f"No task registered for job type '{job.job_type}'."
            )
        async_result = task.delay(str(job.id))
        task_id = str(getattr(async_result, "id", ""))
        if task_id:
            self._dispatch._job_service.mark_queued(job, task_id)
        return job
