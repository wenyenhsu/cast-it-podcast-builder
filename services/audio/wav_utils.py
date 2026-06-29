"""WAV audio utilities."""

import io
import wave


def parse_wav_duration_seconds(data: bytes) -> tuple[int, float]:
    """Return sample rate and duration in seconds from WAV bytes."""
    with wave.open(io.BytesIO(data), "rb") as wav_file:
        frames = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
        duration = frames / float(sample_rate) if sample_rate else 0.0
    return sample_rate, duration
