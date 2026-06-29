"""Audio export service."""

import logging
from pathlib import Path

from domain.audio.pipeline_exceptions import AudioExportError
from infrastructure.media.commands import FFmpegCommands
from infrastructure.media.ffmpeg_runner import FFmpegRunner

logger = logging.getLogger(__name__)


class AudioExportService:
    """Exports processed audio to MP3."""

    def __init__(
        self,
        ffmpeg: FFmpegRunner,
        *,
        default_bitrate: int = 192,
        default_sample_rate: int = 44100,
    ) -> None:
        self._ffmpeg = ffmpeg
        self._default_bitrate = default_bitrate
        self._default_sample_rate = default_sample_rate

    def export_mp3(
        self,
        input_path: Path,
        output_path: Path,
        *,
        bitrate: int | None = None,
        sample_rate: int | None = None,
    ) -> Path:
        """Export the input file as MP3."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        args = FFmpegCommands.export_mp3(
            input_path,
            output_path,
            bitrate=bitrate or self._default_bitrate,
            sample_rate=sample_rate or self._default_sample_rate,
        )
        try:
            result = self._ffmpeg.run(args)
        except Exception as exc:
            raise AudioExportError(
                f"MP3 export failed for {input_path}: {exc}"
            ) from exc

        logger.info(
            "Audio exported to MP3",
            extra={
                "event": "audio_exported_mp3",
                "input_path": str(input_path),
                "output_path": str(output_path),
                "ffmpeg_elapsed_time": result.elapsed_time,
            },
        )
        return output_path
