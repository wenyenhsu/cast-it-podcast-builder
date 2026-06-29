"""TTS request and response data transfer objects."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TTSRequest:
    """Normalized request payload for TTS providers."""

    text: str
    speaker: str = ""
    voice: str = ""
    emotion: str = ""
    language: str = "en"
    speed: float = 1.0
    output_format: str = "wav"


@dataclass(frozen=True)
class TTSResponse:
    """Normalized response from a TTS provider."""

    provider: str
    voice: str
    audio_file: Path
    duration: float
    sample_rate: int
    format: str
    generation_time: float
    bitrate: int | None = None


@dataclass(frozen=True)
class VoiceInfo:
    """Normalized voice metadata from a provider."""

    voice_id: str
    name: str
    language: str = ""
    gender: str = ""


@dataclass(frozen=True)
class ProviderCapabilities:
    """Normalized provider capability metadata."""

    provider: str
    languages: tuple[str, ...]
    formats: tuple[str, ...]
    healthy: bool
