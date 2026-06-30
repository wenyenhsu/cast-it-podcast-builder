"""Job lifecycle management service."""

import logging
import uuid
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.scheduler.models import Job, JobStatus, JobType
from domain.jobs.exceptions import (
    JobCancellationError,
    JobCreationError,
    JobRetryError,
    JobUpdateError,
)
from services.jobs.settings import JobSettings

logger = logging.getLogger(__name__)

CANCELLABLE_STATUSES = frozenset(
    {
        JobStatus.PENDING,
        JobStatus.QUEUED,
        JobStatus.RETRYING,
    }
)

RETRYABLE_STATUSES = frozenset({JobStatus.FAILED})


class JobService:
    """Creates and tracks background job lifecycle state."""

    def __init__(self, settings: JobSettings | None = None) -> None:
        self._settings = settings or JobSettings.from_django_settings()

    @property
    def settings(self) -> JobSettings:
        return self._settings

    @transaction.atomic
    def create_job(
        self,
        job_type: str,
        payload: dict[str, Any] | None = None,
    ) -> Job:
        """Create a new pending job record."""
        try:
            job = Job.objects.create(
                job_type=job_type,
                status=JobStatus.PENDING,
                payload=payload or {},
            )
        except Exception as exc:
            raise JobCreationError(f"Failed to create job: {exc}") from exc

        logger.info(
            "Job created",
            extra={
                "event": "job_created",
                "job_id": str(job.id),
                "job_type": job_type,
            },
        )
        return job

    def get_job(self, job_id: uuid.UUID | str) -> Job:
        """Return a job by id."""
        return Job.objects.get(pk=job_id)

    @transaction.atomic
    def mark_queued(self, job: Job, celery_task_id: str) -> Job:
        """Mark a job as queued with its Celery task id."""
        job.status = JobStatus.QUEUED
        job.celery_task_id = celery_task_id
        if job.progress < 2:
            job.progress = 2
        job.save(update_fields=["status", "celery_task_id", "progress", "updated_at"])
        logger.info(
            "Job queued",
            extra={
                "event": "job_queued",
                "job_id": str(job.id),
                "celery_task_id": celery_task_id,
            },
        )
        return job

    @transaction.atomic
    def mark_running(self, job: Job) -> Job:
        """Mark a job as running."""
        job.status = JobStatus.RUNNING
        if job.started_at is None:
            job.started_at = timezone.now()
        if job.progress < 5:
            job.progress = 5
        job.save(update_fields=["status", "started_at", "progress", "updated_at"])
        logger.info(
            "Job started",
            extra={
                "event": "job_started",
                "job_id": str(job.id),
                "job_type": job.job_type,
            },
        )
        return job

    @transaction.atomic
    def update_progress(self, job: Job, progress: int) -> Job:
        """Update job progress percentage."""
        bounded = max(0, min(100, progress))
        job.progress = bounded
        job.save(update_fields=["progress", "updated_at"])
        logger.info(
            "Job progress updated",
            extra={
                "event": "job_progress_updated",
                "job_id": str(job.id),
                "progress": bounded,
            },
        )
        return job

    @transaction.atomic
    def mark_succeeded(self, job: Job, result: dict[str, Any] | None = None) -> Job:
        """Mark a job as succeeded and store its result."""
        job.status = JobStatus.SUCCEEDED
        job.progress = 100
        job.result = result or {}
        job.completed_at = timezone.now()
        job.error_message = ""
        job.save(
            update_fields=[
                "status",
                "progress",
                "result",
                "completed_at",
                "error_message",
                "updated_at",
            ]
        )
        logger.info(
            "Job succeeded",
            extra={
                "event": "job_succeeded",
                "job_id": str(job.id),
                "job_type": job.job_type,
            },
        )
        return job

    @transaction.atomic
    def mark_failed(
        self,
        job: Job,
        error_message: str,
        *,
        permanent: bool = True,
    ) -> Job:
        """Mark a job as failed."""
        job.status = JobStatus.FAILED
        job.error_message = error_message
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        logger.error(
            "Job failed",
            extra={
                "event": "job_failed",
                "job_id": str(job.id),
                "job_type": job.job_type,
                "permanent": permanent,
                "error": error_message,
            },
        )
        return job

    @transaction.atomic
    def mark_retrying(self, job: Job, error_message: str) -> Job:
        """Mark a job as retrying after a transient failure."""
        job.status = JobStatus.RETRYING
        job.retry_count += 1
        job.error_message = error_message
        job.save(
            update_fields=[
                "status",
                "retry_count",
                "error_message",
                "updated_at",
            ]
        )
        logger.warning(
            "Job retried",
            extra={
                "event": "job_retried",
                "job_id": str(job.id),
                "retry_count": job.retry_count,
                "error": error_message,
            },
        )
        return job

    @transaction.atomic
    def mark_cancelled(self, job: Job, reason: str = "") -> Job:
        """Cancel a job if it is still pending or queued."""
        if job.status not in CANCELLABLE_STATUSES:
            raise JobCancellationError(
                f"Job {job.id} cannot be cancelled from status '{job.status}'."
            )
        job.status = JobStatus.CANCELLED
        job.error_message = reason
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        logger.info(
            "Job cancelled",
            extra={
                "event": "job_cancelled",
                "job_id": str(job.id),
                "reason": reason,
            },
        )
        return job

    @transaction.atomic
    def retry_job(self, job: Job) -> Job:
        """Reset a failed job for retry if retries remain."""
        if job.status not in RETRYABLE_STATUSES:
            raise JobRetryError(
                f"Job {job.id} cannot be retried from status '{job.status}'."
            )
        if job.retry_count >= self._settings.task_max_retries:
            raise JobRetryError(
                f"Job {job.id} exceeded max retries "
                f"({self._settings.task_max_retries})."
            )

        job.status = JobStatus.PENDING
        job.error_message = ""
        job.completed_at = None
        job.celery_task_id = ""
        job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "celery_task_id",
                "updated_at",
            ]
        )
        logger.info(
            "Job reset for retry",
            extra={
                "event": "job_reset_for_retry",
                "job_id": str(job.id),
                "retry_count": job.retry_count,
            },
        )
        return job

    def assign_celery_task_id(self, job: Job, celery_task_id: str) -> Job:
        """Store Celery task id on the job."""
        job.celery_task_id = celery_task_id
        try:
            job.save(update_fields=["celery_task_id", "updated_at"])
        except Exception as exc:
            raise JobUpdateError(
                f"Failed to assign Celery task id to job {job.id}: {exc}"
            ) from exc
        logger.info(
            "Celery task id assigned",
            extra={
                "event": "celery_task_id_assigned",
                "job_id": str(job.id),
                "celery_task_id": celery_task_id,
            },
        )
        return job

    def list_failed_jobs(self, *, limit: int = 100) -> list[Job]:
        """Return failed jobs eligible for retry sweep."""
        return list(
            Job.objects.filter(status=JobStatus.FAILED).order_by("-created_at")[:limit]
        )

    @staticmethod
    def validate_job_type(job_type: str) -> None:
        """Raise if job_type is not a valid choice."""
        valid = {choice.value for choice in JobType}
        if job_type not in valid:
            raise JobCreationError(f"Invalid job type: {job_type}")
