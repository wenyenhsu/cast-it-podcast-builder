"""Tests for job settings."""

from services.jobs.settings import JobSettings


def test_retry_delay_exponential_backoff() -> None:
    settings = JobSettings(
        broker_url="redis://localhost",
        result_backend="redis://localhost",
        task_always_eager=True,
        task_time_limit=3600,
        task_soft_time_limit=3300,
        task_max_retries=3,
        default_queue="default",
        retry_base_delay_seconds=60,
        retry_max_delay_seconds=300,
    )
    assert settings.retry_delay(0) == 60
    assert settings.retry_delay(1) == 120
    assert settings.retry_delay(5) == 300
