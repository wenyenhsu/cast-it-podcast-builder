"""TTS application settings."""

from dataclasses import dataclass, field

from django.conf import settings

from apps.scripts.models import Speaker
from domain.audio.config import TTSProviderConfig


@dataclass(frozen=True)
class TTSSettings:
    """Application-level TTS configuration loaded from environment variables."""

    provider: str
    base_url: str
    timeout: float
    default_voice: str
    audio_format: str
    max_text_length: int
    words_per_minute: int
    storage_subdir: str
    persona_voices: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_django_settings(cls) -> "TTSSettings":
        """Load settings from Django configuration."""
        return cls(
            provider=getattr(settings, "TTS_PROVIDER", "chatterbox"),
            base_url=getattr(
                settings,
                "CHATTERBOX_BASE_URL",
                "http://localhost:8004",
            ),
            timeout=float(getattr(settings, "CHATTERBOX_TIMEOUT", 120.0)),
            default_voice=getattr(settings, "CHATTERBOX_DEFAULT_VOICE", ""),
            audio_format=getattr(settings, "CHATTERBOX_AUDIO_FORMAT", "wav"),
            max_text_length=int(getattr(settings, "TTS_MAX_TEXT_LENGTH", 5000)),
            words_per_minute=int(getattr(settings, "TTS_WORDS_PER_MINUTE", 150)),
            storage_subdir=getattr(settings, "AUDIO_STORAGE_SUBDIR", "audio"),
            persona_voices={
                Speaker.INTRO: getattr(settings, "CHATTERBOX_VOICE_INTRO", ""),
                Speaker.EXPERT: getattr(settings, "CHATTERBOX_VOICE_EXPERT", ""),
                Speaker.BEGINNER: getattr(
                    settings,
                    "CHATTERBOX_VOICE_BEGINNER",
                    "",
                ),
            },
        )

    def to_provider_config(self) -> TTSProviderConfig:
        """Convert to provider-agnostic configuration."""
        return TTSProviderConfig(
            base_url=self.base_url,
            timeout=self.timeout,
            default_voice=self.default_voice,
            audio_format=self.audio_format,
            max_text_length=self.max_text_length,
            words_per_minute=self.words_per_minute,
        )
