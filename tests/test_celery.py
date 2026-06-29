"""Tests for core Celery tasks."""

from apps.core.tasks import ping


def test_ping_task() -> None:
    """Verify the placeholder Celery task returns pong."""
    result = ping()
    assert result == "pong"
