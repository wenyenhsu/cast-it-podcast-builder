"""Background job tracking models."""

from django.db import models

from apps.core.models import DomainModel


class JobType(models.TextChoices):
    IMPORT_NEWS = "import_news", "Import News"
    SUMMARIZE_ARTICLE = "summarize_article", "Summarize Article"
    CLASSIFY_ARTICLE = "classify_article", "Classify Article"
    EPISODE_PLANNING = "episode_planning", "Episode Planning"
    GENERATE_SCRIPT = "generate_script", "Generate Script"
    GENERATE_AUDIO = "generate_audio", "Generate Audio"
    RUN_AUDIO_PIPELINE = "run_audio_pipeline", "Run Audio Pipeline"
    PUBLISH_EPISODE = "publish_episode", "Publish Episode"
    RETRY_JOB = "retry_job", "Retry Job"
    HEALTH_CHECK = "health_check", "Health Check"
    CUSTOM = "custom", "Custom"


class JobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    QUEUED = "queued", "Queued"
    RUNNING = "running", "Running"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"
    CANCELLED = "cancelled", "Cancelled"


class Job(DomainModel):
    """Unified background job tracker synchronized with Celery tasks."""

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
    error_message = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["job_type", "status"]),
            models.Index(fields=["status", "created_at"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(progress__gte=0) & models.Q(progress__lte=100),
                name="job_progress_range",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.job_type} ({self.status})"
