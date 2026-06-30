"""Shared fixtures for API tests."""

from unittest.mock import MagicMock, patch

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    """Return a DRF API test client."""
    return APIClient()


@pytest.fixture
def mock_celery_task() -> MagicMock:
    """Mock Celery task sender returning a fake async result."""
    task = MagicMock()
    async_result = MagicMock()
    async_result.id = "celery-task-id-123"
    task.delay.return_value = async_result
    return task


@pytest.fixture
def mock_job_dispatch(mock_celery_task: MagicMock):
    """Patch task registry and Celery dispatch for async action tests."""
    with patch(
        "api.v1.services.job_dispatch.get_task_for_job_type",
        return_value=mock_celery_task,
    ):
        yield mock_celery_task
