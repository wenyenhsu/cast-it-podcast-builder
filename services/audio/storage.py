"""Audio file storage helpers."""

import hashlib
import shutil
from pathlib import Path

from django.conf import settings


class AudioStorageService:
    """Persists generated audio files under configurable media storage."""

    def __init__(
        self,
        *,
        media_root: Path | None = None,
        storage_subdir: str = "audio",
    ) -> None:
        self._media_root = media_root or Path(
            getattr(settings, "MEDIA_ROOT", Path("media"))
        )
        self._root = self._media_root / storage_subdir

    @property
    def root(self) -> Path:
        return self._root

    def segment_path(
        self,
        episode_id: object,
        sequence: int,
        *,
        output_format: str = "wav",
    ) -> Path:
        """Build the relative storage path for a segment audio file."""
        episode_dir = self._root / str(episode_id)
        filename = f"segment_{sequence:03d}.{output_format.lstrip('.')}"
        return episode_dir / filename

    def save_segment(
        self,
        source_file: Path,
        episode_id: object,
        sequence: int,
        *,
        output_format: str = "wav",
    ) -> tuple[Path, str, int]:
        """Copy generated audio to episode storage and return metadata."""
        destination = self.segment_path(
            episode_id,
            sequence,
            output_format=output_format,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, destination)

        data = destination.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        file_size = len(data)
        return destination, checksum, file_size

    def relative_path(self, absolute_path: Path) -> str:
        """Return a path relative to MEDIA_ROOT when possible."""
        try:
            return str(absolute_path.relative_to(self._media_root))
        except ValueError:
            return str(absolute_path)
