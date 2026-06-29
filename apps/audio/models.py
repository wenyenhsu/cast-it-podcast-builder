"""Audio asset and voice configuration models."""

from django.db import models

from apps.core.models import DomainModel
from apps.scripts.models import Speaker


class AudioAssetStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    GENERATING = "generating", "Generating"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


class VoiceProfile(DomainModel):
    """Provider-agnostic voice configuration stored in the database."""

    name = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=100, db_index=True)
    provider_voice_id = models.CharField(
        max_length=255,
        help_text=(
            "Provider-specific voice identifier " "(never exposed to business callers)."
        ),
    )
    language = models.CharField(max_length=10, default="en", db_index=True)
    gender = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)
    default_speed = models.FloatField(default=1.0)
    enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["provider", "name"]
        indexes = [
            models.Index(fields=["provider", "enabled"]),
            models.Index(fields=["provider", "language"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.provider})"


class PersonaVoiceMapping(DomainModel):
    """Maps script speaker personas to voice profiles."""

    persona = models.CharField(
        max_length=20,
        choices=Speaker.choices,
        db_index=True,
    )
    voice_profile = models.ForeignKey(
        VoiceProfile,
        on_delete=models.CASCADE,
        related_name="persona_mappings",
    )
    provider = models.CharField(max_length=100, db_index=True)
    enabled = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["provider", "persona"]
        constraints = [
            models.UniqueConstraint(
                fields=["persona", "provider"],
                name="unique_persona_provider_voice_mapping",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.persona} -> {self.voice_profile.name}"


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
    voice = models.CharField(max_length=100, blank=True, db_index=True)
    file_path = models.CharField(max_length=500)
    duration = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration in seconds.",
    )
    sample_rate = models.PositiveIntegerField(null=True, blank=True)
    bitrate = models.PositiveIntegerField(null=True, blank=True)
    format = models.CharField(max_length=20, blank=True, db_index=True)
    generation_time = models.FloatField(null=True, blank=True)
    generated_at = models.DateTimeField(null=True, blank=True, db_index=True)
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
