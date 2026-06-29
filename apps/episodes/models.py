"""Episode models."""

from django.db import models

from apps.core.models import DomainModel


class EpisodeStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    COLLECTING = "collecting", "Collecting"
    GENERATING_SCRIPT = "generating_script", "Generating Script"
    GENERATING_AUDIO = "generating_audio", "Generating Audio"
    PUBLISHING = "publishing", "Publishing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class Episode(DomainModel):
    """Represents one podcast episode."""

    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    language = models.CharField(max_length=10, default="en", db_index=True)
    publish_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=30,
        choices=EpisodeStatus.choices,
        default=EpisodeStatus.DRAFT,
        db_index=True,
    )
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    cover_image = models.CharField(max_length=500, blank=True)
    articles = models.ManyToManyField(
        "articles.Article",
        through="episodes.EpisodeArticle",
        related_name="episodes",
        blank=True,
    )

    class Meta:
        ordering = ["-publish_date", "-created_at"]
        indexes = [
            models.Index(fields=["status", "publish_date"]),
        ]

    def __str__(self) -> str:
        return self.title


class EpisodeArticle(models.Model):
    """Many-to-many mapping between episodes and articles."""

    episode = models.ForeignKey(
        Episode,
        on_delete=models.CASCADE,
        related_name="episode_articles",
    )
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.CASCADE,
        related_name="episode_articles",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["episode", "article"],
                name="unique_episode_article",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.episode.title} — {self.article.title}"
