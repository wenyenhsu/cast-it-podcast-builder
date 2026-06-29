"""Celery task handler registry and execution runner."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from apps.scheduler.models import Job, JobStatus
from domain.jobs.exceptions import JobPermanentError, JobTransientError
from services.jobs.job_service import JobService
from services.jobs.settings import JobSettings

logger = logging.getLogger(__name__)

JobHandler = Callable[[Job], dict[str, Any]]


class BaseJobHandler(ABC):
    """Base class for typed job handlers."""

    job_type: str
    queue: str

    @abstractmethod
    def execute(self, job: Job) -> dict[str, Any]:
        """Execute job business logic and return a result payload."""


class JobTaskRunner:
    """Consistent job lifecycle wrapper for Celery tasks."""

    def __init__(
        self,
        job_service: JobService | None = None,
        settings: JobSettings | None = None,
    ) -> None:
        self._job_service = job_service or JobService()
        self._settings = settings or JobSettings.from_django_settings()

    @property
    def job_service(self) -> JobService:
        return self._job_service

    def run(self, job_id: str, handler: JobHandler) -> dict[str, Any]:
        """Load a job, execute handler, and update lifecycle state."""
        job = self._job_service.get_job(job_id)

        if job.status == JobStatus.CANCELLED:
            logger.info(
                "Job skipped, cancelled",
                extra={"event": "job_skipped_cancelled", "job_id": job_id},
            )
            return {"skipped": True, "reason": "cancelled"}

        self._job_service.mark_running(job)
        try:
            result = handler(job)
            self._job_service.mark_succeeded(job, result)
            return result
        except JobPermanentError as exc:
            self._job_service.mark_failed(job, str(exc), permanent=True)
            raise
        except JobTransientError as exc:
            if job.retry_count < self._settings.task_max_retries:
                self._job_service.mark_retrying(job, str(exc))
            else:
                self._job_service.mark_failed(
                    job,
                    f"Max retries exceeded: {exc}",
                    permanent=True,
                )
            raise
        except Exception as exc:
            self._job_service.mark_failed(job, str(exc), permanent=True)
            logger.exception(
                "Job execution failed unexpectedly",
                extra={"event": "job_execution_error", "job_id": job_id},
            )
            raise

    def run_handler(self, job_id: str, handler: BaseJobHandler) -> dict[str, Any]:
        """Execute a BaseJobHandler through the standard lifecycle."""
        return self.run(job_id, handler.execute)
