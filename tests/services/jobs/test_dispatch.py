"""Tests for job dispatch service."""

from unittest.mock import MagicMock

from apps.scheduler.models import JobStatus, JobType
from services.jobs.dispatch import JobDispatchService


def test_create_and_dispatch(db: None) -> None:
    mock_task = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "celery-task-abc"
    mock_task.delay.return_value = mock_result

    job = JobDispatchService().create_and_dispatch(
        JobType.HEALTH_CHECK,
        mock_task,
        payload={"scheduled": True},
    )

    assert job.status == JobStatus.QUEUED
    assert job.celery_task_id == "celery-task-abc"
    mock_task.delay.assert_called_once_with(str(job.id))
