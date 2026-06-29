"""Tests for job service."""

import pytest

from apps.scheduler.models import Job, JobStatus, JobType
from domain.jobs.exceptions import (
    JobCancellationError,
    JobCreationError,
    JobRetryError,
)
from services.jobs.job_service import JobService


@pytest.fixture
def job_service() -> JobService:
    return JobService()


def test_create_job(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.HEALTH_CHECK, {"check": True})
    assert job.status == JobStatus.PENDING
    assert job.payload == {"check": True}


def test_mark_lifecycle(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.IMPORT_NEWS, {})
    job_service.mark_queued(job, "task-123")
    job.refresh_from_db()
    assert job.status == JobStatus.QUEUED
    assert job.celery_task_id == "task-123"

    job_service.mark_running(job)
    job.refresh_from_db()
    assert job.status == JobStatus.RUNNING
    assert job.started_at is not None

    job_service.update_progress(job, 50)
    job.refresh_from_db()
    assert job.progress == 50

    job_service.mark_succeeded(job, {"imported_count": 3})
    job.refresh_from_db()
    assert job.status == JobStatus.SUCCEEDED
    assert job.progress == 100
    assert job.result == {"imported_count": 3}


def test_mark_failed(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.GENERATE_SCRIPT, {})
    job_service.mark_failed(job, "Permanent failure")
    job.refresh_from_db()
    assert job.status == JobStatus.FAILED
    assert job.error_message == "Permanent failure"


def test_mark_retrying(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.GENERATE_AUDIO, {})
    job_service.mark_retrying(job, "Transient error")
    job.refresh_from_db()
    assert job.status == JobStatus.RETRYING
    assert job.retry_count == 1


def test_cancel_job(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.PUBLISH_EPISODE, {})
    job_service.mark_cancelled(job, "User request")
    job.refresh_from_db()
    assert job.status == JobStatus.CANCELLED


def test_cancel_running_job_raises(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.PUBLISH_EPISODE, {})
    job_service.mark_running(job)
    with pytest.raises(JobCancellationError):
        job_service.mark_cancelled(job)


def test_retry_job(job_service: JobService, db: None) -> None:
    job = job_service.create_job(JobType.SUMMARIZE_ARTICLE, {"article_id": "1"})
    job_service.mark_failed(job, "failed")
    job_service.retry_job(job)
    job.refresh_from_db()
    assert job.status == JobStatus.PENDING


def test_retry_job_max_retries_raises(job_service: JobService, db: None) -> None:
    job = Job.objects.create(
        job_type=JobType.CLASSIFY_ARTICLE,
        status=JobStatus.FAILED,
        retry_count=3,
    )
    with pytest.raises(JobRetryError):
        job_service.retry_job(job)


def test_invalid_job_type_raises(job_service: JobService) -> None:
    with pytest.raises(JobCreationError):
        job_service.validate_job_type("invalid_type")
