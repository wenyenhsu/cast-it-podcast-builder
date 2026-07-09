"""Script generation models."""

from django.db import models

from apps.core.models import DomainModel


class ScriptStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    APPROVED = "approved", "Approved"
    FAILED = "failed", "Failed"


class ValidationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PASSED = "passed", "Passed"
    FAILED = "failed", "Failed"


class Speaker(models.TextChoices):
    EXPERT = "expert", "Expert"
    BEGINNER = "beginner", "Beginner"
    NARRATION = "narration", "Narration"
    INTRO = "intro", "Intro"
    OUTRO = "outro", "Outro"


class Script(DomainModel):
    """Represents one generated script version for an episode."""

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="scripts",
    )
    version = models.PositiveIntegerField(default=1)
    title = models.CharField(max_length=500, blank=True)
    llm_provider = models.CharField(max_length=100, blank=True)
    model_name = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=50, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ScriptStatus.choices,
        default=ScriptStatus.DRAFT,
        db_index=True,
    )
    validation_status = models.CharField(
        max_length=20,
        choices=ValidationStatus.choices,
        default=ValidationStatus.PENDING,
        db_index=True,
    )
    estimated_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["episode", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["episode", "version"],
                name="unique_episode_script_version",
            ),
        ]
        indexes = [
            models.Index(fields=["episode", "status"]),
            models.Index(fields=["episode", "validation_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.episode.title} v{self.version}"


class ScriptMetadata(DomainModel):
    """Generation and validation metadata for a script."""

    script = models.OneToOneField(
        Script,
        on_delete=models.CASCADE,
        related_name="metadata",
    )
    is_active = models.BooleanField(default=False, db_index=True)
    source_article_ids = models.JSONField(default=list, blank=True)
    selected_topics = models.JSONField(default=list, blank=True)
    generation_notes = models.TextField(blank=True)
    token_usage = models.JSONField(default=dict, blank=True)
    validation_results = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name_plural = "script metadata"

    def __str__(self) -> str:
        return f"Metadata for {self.script}"


class ScriptSegment(DomainModel):
    """Represents one dialogue segment within a script."""

    script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE,
        related_name="segments",
    )
    article = models.ForeignKey(
        "articles.Article",
        on_delete=models.SET_NULL,
        related_name="script_segments",
        null=True,
        blank=True,
        help_text="Source article this segment discusses (chaptered generation).",
    )
    sequence = models.PositiveIntegerField()
    speaker = models.CharField(
        max_length=20,
        choices=Speaker.choices,
        db_index=True,
    )
    voice = models.CharField(max_length=100, blank=True)
    emotion = models.CharField(max_length=50, blank=True)
    text = models.TextField()
    pause_before_seconds = models.FloatField(default=0.0)
    pause_after_seconds = models.FloatField(default=0.0)
    estimated_duration_seconds = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["script", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["script", "sequence"],
                name="unique_script_segment_sequence",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.script} #{self.sequence} ({self.speaker})"
