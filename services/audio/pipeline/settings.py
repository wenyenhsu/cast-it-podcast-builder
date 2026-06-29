"""Audio pipeline configuration."""

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass(frozen=True)
class AudioSettings:
    """Application-level audio pipeline configuration."""

    output_subdir: str
    default_bitrate: int
    default_sample_rate: int
    default_silence_seconds: float
    intro_file_path: str
    outro_file_path: str
    background_music_path: str
    enable_background_music: bool
    enable_normalization: bool
    background_music_volume: float
    ffmpeg_binary: str
    ffprobe_binary: str
    ffmpeg_timeout: float
    target_lufs: float

    @classmethod
    def from_django_settings(cls) -> "AudioSettings":
        """Load settings from Django configuration."""
        return cls(
            output_subdir=getattr(settings, "AUDIO_OUTPUT_SUBDIR", "audio"),
            default_bitrate=int(getattr(settings, "AUDIO_DEFAULT_BITRATE", 192)),
            default_sample_rate=int(
                getattr(settings, "AUDIO_DEFAULT_SAMPLE_RATE", 44100)
            ),
            default_silence_seconds=float(
                getattr(settings, "AUDIO_DEFAULT_SILENCE_SECONDS", 0.75)
            ),
            intro_file_path=getattr(settings, "AUDIO_INTRO_FILE_PATH", ""),
            outro_file_path=getattr(settings, "AUDIO_OUTRO_FILE_PATH", ""),
            background_music_path=getattr(settings, "AUDIO_BACKGROUND_MUSIC_PATH", ""),
            enable_background_music=bool(
                getattr(settings, "AUDIO_ENABLE_BACKGROUND_MUSIC", False)
            ),
            enable_normalization=bool(
                getattr(settings, "AUDIO_ENABLE_NORMALIZATION", True)
            ),
            background_music_volume=float(
                getattr(settings, "AUDIO_BACKGROUND_MUSIC_VOLUME", 0.15)
            ),
            ffmpeg_binary=getattr(settings, "FFMPEG_BINARY", "ffmpeg"),
            ffprobe_binary=getattr(settings, "FFPROBE_BINARY", "ffprobe"),
            ffmpeg_timeout=float(getattr(settings, "FFMPEG_TIMEOUT", 300.0)),
            target_lufs=float(getattr(settings, "AUDIO_TARGET_LUFS", -16.0)),
        )

    @property
    def media_root(self) -> Path:
        return Path(getattr(settings, "MEDIA_ROOT", Path("media")))

    def resolve_optional_path(self, path_value: str) -> Path | None:
        """Resolve an optional configured file path."""
        if not path_value.strip():
            return None
        path = Path(path_value)
        if path.is_absolute():
            return path
        return self.media_root / path
