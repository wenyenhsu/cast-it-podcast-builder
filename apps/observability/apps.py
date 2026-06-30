"""Observability Django application."""

from django.apps import AppConfig


class ObservabilityConfig(AppConfig):
    """Application configuration for observability."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.observability"
    verbose_name = "Observability"

    def ready(self) -> None:
        import services.observability.celery_hooks  # noqa: F401
