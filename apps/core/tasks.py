"""Core application tasks."""

from celery import shared_task


@shared_task(name="core.ping")  # type: ignore[untyped-decorator]
def ping() -> str:
    """Placeholder task to verify Celery pipeline works."""
    return "pong"
