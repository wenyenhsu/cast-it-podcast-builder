"""Audio metadata calculation and persistence helpers."""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone

from apps.audio.models import AudioAsset, AudioAssetStatus
from infrastructure.media.ffmpeg_runner import FFprobeRunner
from services.audio.storage import AudioStorageService

logger = logging.getLogger(__name__)

EpisodeId = uuid.UUID | str


@dataclass(frozen=True)
class AudioFileMetadata:
    """Computed metadata for a generated audio file."""

    duration_seconds: int
    file_size: int
    checksum: str
    sample_rate: int
    bitrate: int | None
    format: str
    codec: str


class AudioMetadataService:
    """Calculates and persists audio file metadata."""

    def __init__(
        self,
        ffprobe: FFprobeRunner | None = None,
        storage: AudioStorageService | None = None,
    ) -> None:
        self._ffprobe = ffprobe or FFprobeRunner()
        self._storage = storage or AudioStorageService()

    def calculate(self, file_path: Path) -> AudioFileMetadata:
        """Calculate metadata for an audio file."""
        data = file_path.read_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        probe = self._ffprobe.probe(file_path)

        return AudioFileMetadata(
            duration_seconds=max(1, int(round(probe.duration_seconds))),
            file_size=len(data),
            checksum=checksum,
            sample_rate=probe.sample_rate,
            bitrate=probe.bitrate,
            format=file_path.suffix.lstrip(".") or probe.format_name,
            codec=probe.codec,
        )

    def create_final_asset(
        self,
        *,
        episode_id: EpisodeId,
        absolute_path: Path,
        provider: str = "ffmpeg",
    ) -> AudioAsset:
        """Persist a final episode audio asset record."""
        metadata = self.calculate(absolute_path)
        relative_path = self._storage.relative_path(absolute_path)

        asset = AudioAsset.objects.create(
            episode_id=episode_id,
            script_segment=None,
            provider=provider,
            file_path=relative_path,
            duration=metadata.duration_seconds,
            sample_rate=metadata.sample_rate,
            bitrate=metadata.bitrate,
            format=metadata.format,
            file_size=metadata.file_size,
            checksum=metadata.checksum,
            status=AudioAssetStatus.READY,
            is_final_episode_audio=True,
            generated_at=timezone.now(),
        )

        logger.info(
            "Final episode audio metadata persisted",
            extra={
                "event": "final_audio_metadata_persisted",
                "episode_id": str(episode_id),
                "audio_asset_id": str(asset.id),
                "duration_seconds": metadata.duration_seconds,
                "file_path": relative_path,
            },
        )
        return asset
