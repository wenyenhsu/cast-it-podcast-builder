"""Audio asset models."""

from django.db import models

from apps.core.models import DomainModel


class AudioAssetStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class AudioAsset(DomainModel):
    """Represents generated audio for a segment or full episode."""

    episode = models.ForeignKey(
        "episodes.Episode",
        on_delete=models.CASCADE,
        related_name="audio_assets",
    )
    script_segment = models.ForeignKey(
        "scripts.ScriptSegment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audio_assets",
    )
    provider = models.CharField(max_length=100, blank=True, db_index=True)
    file_path = models.CharField(max_length=500)
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds.",
    )
    file_size = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes.",
    )
    checksum = models.CharField(max_length=64, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=AudioAssetStatus.choices,
        default=AudioAssetStatus.PENDING,
        db_index=True,
    )

    class Meta:
        ordering = ["episode", "-created_at"]
        indexes = [
            models.Index(fields=["episode", "status"]),
            models.Index(fields=["episode", "script_segment"]),
        ]

    def __str__(self) -> str:
        if self.script_segment_id:
            return f"Segment audio — {self.episode.title}"
        return f"Episode audio — {self.episode.title}"
