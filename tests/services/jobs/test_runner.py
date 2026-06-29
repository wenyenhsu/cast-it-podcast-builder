"""Tests for job task runner."""

from unittest.mock import MagicMock

import pytest

from apps.scheduler.models import JobStatus, JobType
from domain.jobs.exceptions import JobPermanentError, JobTransientError
from infrastructure.jobs.runner import JobTaskRunner
from services.jobs.job_service import JobService


def _ok_handler(_job: object) -> dict[str, bool]:
    return {"ok": True}


def _permanent_error_handler(_job: object) -> dict[str, bool]:
    raise JobPermanentError("bad")


def _transient_error_handler(_job: object) -> dict[str, bool]:
    raise JobTransientError("temporary")


def test_runner_executes_handler_successfully(db: None) -> None:
    service = JobService()
    job = service.create_job(JobType.HEALTH_CHECK, {})
    runner = JobTaskRunner(job_service=service)

    result = runner.run(str(job.id), _ok_handler)

    assert result == {"ok": True}
    job.refresh_from_db()
    assert job.status == JobStatus.SUCCEEDED


def test_runner_marks_permanent_failure(db: None) -> None:
    service = JobService()
    job = service.create_job(JobType.GENERATE_SCRIPT, {})
    runner = JobTaskRunner(job_service=service)

    with pytest.raises(JobPermanentError):
        runner.run(str(job.id), _permanent_error_handler)

    job.refresh_from_db()
    assert job.status == JobStatus.FAILED


def test_runner_marks_retrying_on_transient_error(db: None) -> None:
    service = JobService()
    job = service.create_job(JobType.GENERATE_AUDIO, {})
    runner = JobTaskRunner(job_service=service)

    with pytest.raises(JobTransientError):
        runner.run(str(job.id), _transient_error_handler)

    job.refresh_from_db()
    assert job.status == JobStatus.RETRYING


def test_runner_skips_cancelled_job(db: None) -> None:
    service = JobService()
    job = service.create_job(JobType.IMPORT_NEWS, {})
    service.mark_cancelled(job)
    runner = JobTaskRunner(job_service=service)
    handler = MagicMock()

    result = runner.run(str(job.id), handler)

    assert result["skipped"] is True
    handler.assert_not_called()
