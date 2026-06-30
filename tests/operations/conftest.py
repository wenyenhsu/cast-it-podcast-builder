"""Shared fixtures for operations dashboard tests."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_celery_task() -> MagicMock:
    task = MagicMock()
    async_result = MagicMock()
    async_result.id = "celery-task-id-123"
    task.delay.return_value = async_result
    return task


@pytest.fixture
def mock_job_dispatch(mock_celery_task: MagicMock):
    with patch(
        "api.v1.services.job_dispatch.get_task_for_job_type",
        return_value=mock_celery_task,
    ):
        yield mock_celery_task
