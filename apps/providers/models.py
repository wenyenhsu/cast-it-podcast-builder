"""Content provider models."""

from django.db import models

from apps.core.models import DomainModel


class ProviderType(models.TextChoices):
    RSS = "rss", "RSS"
    HTML = "html", "HTML"
    API = "api", "API"
    MANUAL = "manual", "Manual"


class NewsSource(DomainModel):
    """Represents where a collected article originated."""

    name = models.CharField(max_length=255)
    provider_type = models.CharField(
        max_length=20,
        choices=ProviderType.choices,
        db_index=True,
    )
    homepage = models.URLField(max_length=500, blank=True)
    rss_url = models.URLField(max_length=500, blank=True)
    language = models.CharField(max_length=10, default="en", db_index=True)
    enabled = models.BooleanField(default=True, db_index=True)
    max_articles_per_import = models.PositiveSmallIntegerField(
        default=0,
        help_text="Maximum articles to import per run (0 = no limit).",
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["enabled", "provider_type"]),
        ]

    def __str__(self) -> str:
        return self.name


class ProviderHealthStatus(models.TextChoices):
    HEALTHY = "healthy", "Healthy"
    UNHEALTHY = "unhealthy", "Unhealthy"
    UNKNOWN = "unknown", "Unknown"


class ProviderHealthCheck(DomainModel):
    """Stores the result of a provider health check."""

    news_source = models.ForeignKey(
        NewsSource,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="health_checks",
    )
    provider_type = models.CharField(max_length=50, db_index=True)
    provider_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=ProviderHealthStatus.choices,
        default=ProviderHealthStatus.UNKNOWN,
        db_index=True,
    )
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    checked_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-checked_at"]
        indexes = [
            models.Index(fields=["provider_type", "status"]),
            models.Index(fields=["news_source", "checked_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.provider_name} ({self.status})"
