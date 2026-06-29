"""Loudness normalization service."""

import logging
from pathlib import Path

from domain.audio.pipeline_exceptions import AudioNormalizationError
from infrastructure.media.commands import FFmpegCommands
from infrastructure.media.ffmpeg_runner import FFmpegRunner

logger = logging.getLogger(__name__)


class AudioNormalizationService:
    """Normalizes segment loudness using FFmpeg loudnorm."""

    def __init__(
        self,
        ffmpeg: FFmpegRunner,
        *,
        target_lufs: float = -16.0,
        enabled: bool = True,
    ) -> None:
        self._ffmpeg = ffmpeg
        self._target_lufs = target_lufs
        self._enabled = enabled

    def normalize(self, input_path: Path, output_path: Path) -> Path:
        """Normalize a single audio file."""
        if not self._enabled:
            output_path.write_bytes(input_path.read_bytes())
            return output_path

        args = FFmpegCommands.loudnorm(
            input_path,
            output_path,
            target_lufs=self._target_lufs,
        )
        try:
            result = self._ffmpeg.run(args)
        except Exception as exc:
            raise AudioNormalizationError(
                f"Normalization failed for {input_path}: {exc}"
            ) from exc

        logger.info(
            "Audio normalized",
            extra={
                "event": "audio_normalized",
                "input_path": str(input_path),
                "output_path": str(output_path),
                "ffmpeg_elapsed_time": result.elapsed_time,
            },
        )
        return output_path

    def normalize_many(
        self,
        input_paths: list[Path],
        output_dir: Path,
    ) -> list[Path]:
        """Normalize multiple files into the output directory."""
        normalized: list[Path] = []
        for index, input_path in enumerate(input_paths, start=1):
            output_path = output_dir / f"normalized_{index:03d}{input_path.suffix}"
            normalized.append(self.normalize(input_path, output_path))
        return normalized
