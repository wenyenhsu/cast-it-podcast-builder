"""Job and Celery settings."""

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class JobSettings:
    """Application-level job and Celery configuration."""

    broker_url: str
    result_backend: str
    task_always_eager: bool
    task_time_limit: int
    task_soft_time_limit: int
    task_max_retries: int
    default_queue: str
    retry_base_delay_seconds: int
    retry_max_delay_seconds: int

    @classmethod
    def from_django_settings(cls) -> "JobSettings":
        """Load settings from Django configuration."""
        return cls(
            broker_url=getattr(settings, "CELERY_BROKER_URL", ""),
            result_backend=getattr(settings, "CELERY_RESULT_BACKEND", ""),
            task_always_eager=bool(
                getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False)
            ),
            task_time_limit=int(getattr(settings, "CELERY_TASK_TIME_LIMIT", 3600)),
            task_soft_time_limit=int(
                getattr(settings, "CELERY_TASK_SOFT_TIME_LIMIT", 3300)
            ),
            task_max_retries=int(getattr(settings, "CELERY_TASK_MAX_RETRIES", 3)),
            default_queue=getattr(settings, "CELERY_DEFAULT_QUEUE", "default"),
            retry_base_delay_seconds=int(
                getattr(settings, "CELERY_RETRY_BASE_DELAY", 60)
            ),
            retry_max_delay_seconds=int(
                getattr(settings, "CELERY_RETRY_MAX_DELAY", 900)
            ),
        )

    def retry_delay(self, retry_count: int) -> int:
        """Calculate exponential backoff delay capped at max delay."""
        delay = self.retry_base_delay_seconds * (2**retry_count)
        return int(min(delay, self.retry_max_delay_seconds))
