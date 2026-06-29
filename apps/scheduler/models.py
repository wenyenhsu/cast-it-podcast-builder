"""Background job tracking models."""

from django.db import models

from apps.core.models import UUIDModel


class JobType(models.TextChoices):
    COLLECT_ARTICLES = "collect_articles", "Collect Articles"
    GENERATE_SCRIPT = "generate_script", "Generate Script"
    GENERATE_AUDIO = "generate_audio", "Generate Audio"
    PUBLISH_EPISODE = "publish_episode", "Publish Episode"
    CUSTOM = "custom", "Custom"


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    RUNNING = "running", "Running"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"
    CANCELLED = "cancelled", "Cancelled"


class Job(UUIDModel):
    """Generic background job tracker. Celery integration will be added later."""

    job_type = models.CharField(
        max_length=30,
        choices=JobType.choices,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=JobStatus.choices,
        default=JobStatus.PENDING,
        db_index=True,
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        help_text="Progress percentage from 0 to 100.",
    )
    payload = models.JSONField(default=dict, blank=True)
    result = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at", "-id"]
        indexes = [
            models.Index(fields=["job_type", "status"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress__gte=0) & models.Q(progress__lte=100),
                name="job_progress_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.job_type} ({self.status})"
