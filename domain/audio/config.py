"""TTS provider configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TTSProviderConfig:
    """Provider-agnostic TTS configuration."""

    base_url: str
    timeout: float
    default_voice: str
    audio_format: str
    max_text_length: int = 5000
    words_per_minute: int = 150
