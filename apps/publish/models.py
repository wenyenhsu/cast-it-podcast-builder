"""Publishing models."""

from django.db import models

from apps.core.models import DomainModel


class Platform(models.TextChoices):
    YOUTUBE = "youtube", "YouTube"
    RSS = "rss", "RSS"
    SPOTIFY = "spotify", "Spotify"
    APPLE_PODCASTS = "apple_podcasts", "Apple Podcasts"
    TWITCH = "twitch", "Twitch"
    WEBAPP = "webapp", "Web App"
    MOBILE_APP = "mobile_app", "Mobile App"


class PublishJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class PublishJob(DomainModel):
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
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["episode", "platform"]),
            models.Index(fields=["status", "platform"]),
        ]

    def __str__(self) -> str:
        return f"{self.episode.title} → {self.platform} ({self.status})"


class PublishedEpisode(DomainModel):
    """Successful publication history for an episode on a platform."""

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="published_episodes",
    )
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        db_index=True,
    )
    published_url = models.URLField(max_length=1000)
    external_id = models.CharField(max_length=255, blank=True, db_index=True)
    published_at = models.DateTimeField(db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-published_at"]
        indexes = [
            models.Index(fields=["episode", "platform"]),
            models.Index(fields=["platform", "published_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.episode.title} on {self.platform}"
