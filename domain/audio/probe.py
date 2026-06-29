"""Media processing probe results."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioProbeResult:
    """Normalized audio file metadata from FFprobe."""

    duration_seconds: float
    sample_rate: int
    bitrate: int | None
    codec: str
    format_name: str
