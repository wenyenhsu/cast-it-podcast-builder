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

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["enabled", "provider_type"]),
        ]

    def __str__(self) -> str:
        return self.name
