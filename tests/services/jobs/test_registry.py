"""Tests for task registry."""

from apps.scheduler.tasks.registry import get_task_for_job_type, register_task


def test_register_and_get_task() -> None:
    sentinel = object()
    register_task("test_job", sentinel)
    assert get_task_for_job_type("test_job") is sentinel
