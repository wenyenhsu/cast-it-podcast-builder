"""Audio file validation for the pipeline."""

import logging
from pathlib import Path

from apps.audio.models import AudioAsset
from domain.audio.pipeline_exceptions import AudioValidationError
from infrastructure.media.ffmpeg_runner import FFprobeRunner

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset({".wav", ".mp3", ".opus", ".ogg", ".flac", ".m4a"})
MIN_FILE_SIZE_BYTES = 44


class AudioValidationService:
    """Validates segment audio files before pipeline processing."""

    def __init__(
        self,
        ffprobe: FFprobeRunner | None = None,
        *,
        supported_extensions: frozenset[str] | None = None,
        min_file_size_bytes: int = MIN_FILE_SIZE_BYTES,
    ) -> None:
        self._ffprobe = ffprobe or FFprobeRunner()
        self._supported_extensions = supported_extensions or SUPPORTED_EXTENSIONS
        self._min_file_size_bytes = min_file_size_bytes

    def validate_file(self, file_path: Path) -> None:
        """Validate a single audio file on disk."""
        if not file_path.exists():
            raise AudioValidationError(f"Audio file does not exist: {file_path}")

        if not file_path.is_file():
            raise AudioValidationError(f"Path is not a file: {file_path}")

        extension = file_path.suffix.lower()
        if extension not in self._supported_extensions:
            raise AudioValidationError(
                f"Unsupported audio extension '{extension}' for {file_path}."
            )

        file_size = file_path.stat().st_size
        if file_size < self._min_file_size_bytes:
            raise AudioValidationError(
                f"Audio file is too small ({file_size} bytes): {file_path}"
            )

        probe = self._ffprobe.probe(file_path)
        if probe.duration_seconds <= 0:
            raise AudioValidationError(f"Audio file has invalid duration: {file_path}")

        logger.debug(
            "Audio file validated",
            extra={
                "event": "audio_file_validated",
                "file_path": str(file_path),
                "duration_seconds": probe.duration_seconds,
            },
        )

    def validate_assets(
        self,
        assets: list[AudioAsset],
        resolved_paths: list[Path],
    ) -> None:
        """Validate a ordered list of segment audio assets."""
        if not assets:
            raise AudioValidationError("No segment audio assets provided.")

        if len(assets) != len(resolved_paths):
            raise AudioValidationError(
                "Asset count does not match resolved path count."
            )

        for asset, path in zip(assets, resolved_paths, strict=True):
            if asset.script_segment_id is None:
                raise AudioValidationError(
                    f"Asset {asset.id} is not linked to a script segment."
                )
            self.validate_file(path)

        logger.info(
            "Segment audio assets validated",
            extra={
                "event": "segment_assets_validated",
                "segment_count": len(assets),
            },
        )

    def validate_optional_file(self, file_path: Path | None, label: str) -> None:
        """Validate an optional intro, outro, or music file."""
        if file_path is None:
            return
        try:
            self.validate_file(file_path)
        except AudioValidationError as exc:
            raise AudioValidationError(f"{label} validation failed: {exc}") from exc
