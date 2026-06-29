"""Publishing models."""

from django.db import models

from apps.core.models import UUIDModel


class Platform(models.TextChoices):
    YOUTUBE = "youtube", "YouTube"
    RSS = "rss", "RSS"
    SPOTIFY = "spotify", "Spotify"
    TWITCH = "twitch", "Twitch"
    WEBAPP = "webapp", "Web App"


class PublishJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class PublishJob(UUIDModel):
    """Represents a publishing attempt for an episode on a platform."""

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="publish_jobs",
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=PublishJobStatus.choices,
        default=PublishJobStatus.PENDING,
        db_index=True,
    )
    published_url = models.URLField(max_length=1000, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["episode", "platform"]),
            models.Index(fields=["status", "platform"]),
        ]

    def __str__(self) -> str:
        return f"{self.episode.title} → {self.platform} ({self.status})"
