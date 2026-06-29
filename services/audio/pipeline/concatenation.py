"""Audio concatenation service."""

import logging
from pathlib import Path

from domain.audio.pipeline_exceptions import AudioConcatenationError
from infrastructure.media.commands import FFmpegCommands
from infrastructure.media.ffmpeg_runner import FFmpegRunner
from services.audio.utils.paths import build_concat_list_content

logger = logging.getLogger(__name__)


class AudioConcatenationService:
    """Concatenates audio parts with silence, intro, and outro."""

    def __init__(
        self,
        ffmpeg: FFmpegRunner,
        *,
        silence_seconds: float = 0.75,
        sample_rate: int = 44100,
    ) -> None:
        self._ffmpeg = ffmpeg
        self._silence_seconds = silence_seconds
        self._sample_rate = sample_rate

    def concatenate(
        self,
        segment_paths: list[Path],
        output_path: Path,
        *,
        workspace: Path,
        intro_path: Path | None = None,
        outro_path: Path | None = None,
    ) -> Path:
        """Concatenate segments with optional intro/outro and silence gaps."""
        if not segment_paths:
            raise AudioConcatenationError(
                "No segment paths provided for concatenation."
            )

        try:
            parts: list[Path] = []
            if intro_path is not None:
                parts.append(intro_path)

            for index, segment_path in enumerate(segment_paths):
                parts.append(segment_path)
                if index < len(segment_paths) - 1 and self._silence_seconds > 0:
                    silence_path = workspace / f"silence_{index:03d}.wav"
                    self._generate_silence(silence_path)
                    parts.append(silence_path)

            if outro_path is not None:
                parts.append(outro_path)

            concat_list_path = workspace / "concat_list.txt"
            concat_list_path.write_text(
                build_concat_list_content(parts),
                encoding="utf-8",
            )
            args = FFmpegCommands.concat_demuxer(concat_list_path, output_path)
            result = self._ffmpeg.run(args)
        except AudioConcatenationError:
            raise
        except Exception as exc:
            raise AudioConcatenationError(f"Concatenation failed: {exc}") from exc

        logger.info(
            "Audio concatenated",
            extra={
                "event": "audio_concatenated",
                "segment_count": len(segment_paths),
                "output_path": str(output_path),
                "ffmpeg_elapsed_time": result.elapsed_time,
            },
        )
        return output_path

    def mix_background_music(
        self,
        speech_path: Path,
        music_path: Path,
        output_path: Path,
        *,
        music_volume: float = 0.15,
        fade_in_seconds: float = 2.0,
        fade_out_seconds: float = 3.0,
    ) -> Path:
        """Mix background music under the concatenated speech track."""
        try:
            args = FFmpegCommands.mix_background_music(
                speech_path,
                music_path,
                output_path,
                music_volume=music_volume,
                fade_in_seconds=fade_in_seconds,
                fade_out_seconds=fade_out_seconds,
            )
            result = self._ffmpeg.run(args)
        except Exception as exc:
            raise AudioConcatenationError(
                f"Background music mixing failed: {exc}"
            ) from exc

        logger.info(
            "Background music mixed",
            extra={
                "event": "background_music_mixed",
                "output_path": str(output_path),
                "ffmpeg_elapsed_time": result.elapsed_time,
            },
        )
        return output_path

    def _generate_silence(self, output_path: Path) -> None:
        args = FFmpegCommands.generate_silence(
            output_path,
            duration_seconds=self._silence_seconds,
            sample_rate=self._sample_rate,
        )
        self._ffmpeg.run(args)
