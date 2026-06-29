"""Job dispatch service."""

import logging
from typing import Any, Protocol

from apps.scheduler.models import Job
from services.jobs.job_service import JobService

logger = logging.getLogger(__name__)


class CeleryTaskSender(Protocol):
    """Protocol for sending Celery tasks (used in tests)."""

    def delay(self, job_id: str) -> object: ...


class JobDispatchService:
    """Creates jobs and dispatches them to Celery tasks."""

    def __init__(self, job_service: JobService | None = None) -> None:
        self._job_service = job_service or JobService()

    def create_and_dispatch(
        self,
        job_type: str,
        task_sender: CeleryTaskSender,
        payload: dict[str, Any] | None = None,
    ) -> Job:
        """Create a job record and enqueue the corresponding Celery task."""
        self._job_service.validate_job_type(job_type)
        job = self._job_service.create_job(job_type, payload)
        async_result = task_sender.delay(str(job.id))
        task_id = str(getattr(async_result, "id", ""))
        if task_id:
            self._job_service.mark_queued(job, task_id)
        logger.info(
            "Job dispatched",
            extra={
                "event": "job_dispatched",
                "job_id": str(job.id),
                "job_type": job_type,
                "celery_task_id": task_id,
            },
        )
        return job
