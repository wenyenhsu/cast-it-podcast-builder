"""Script generation models."""

from django.db import models

from apps.core.models import DomainModel, UUIDModel


class ScriptStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    APPROVED = "approved", "Approved"
    FAILED = "failed", "Failed"


class Speaker(models.TextChoices):
    EXPERT = "expert", "Expert"
    BEGINNER = "beginner", "Beginner"


class Script(DomainModel):
    """Represents one generated script version for an episode."""

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="scripts",
    )
    version = models.PositiveIntegerField(default=1)
    llm_provider = models.CharField(max_length=100, blank=True)
    prompt_version = models.CharField(max_length=50, blank=True)
    status = models.CharField(
        max_length=20,
        choices=ScriptStatus.choices,
        default=ScriptStatus.DRAFT,
        db_index=True,
    )

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
        ]

    def __str__(self) -> str:
        return f"{self.episode.title} v{self.version}"


class ScriptSegment(UUIDModel):
    """Represents one dialogue segment within a script."""

    script = models.ForeignKey(
        Script,
        on_delete=models.CASCADE,
        related_name="segments",
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
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)

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
