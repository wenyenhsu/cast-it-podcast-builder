"""Per-chapter audio asset construction.

After segment TTS audio exists, this service groups segments by their source
article (set during chaptered script generation) and builds one standalone
MP3 per article. These chapter assets are the shared building blocks for
personalized listener feeds: generated once per day, assembled per user.
"""

import logging
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.utils import timezone

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode
from services.audio.pipeline.concatenation import AudioConcatenationService
from services.audio.pipeline.export import AudioExportService
from services.audio.pipeline.metadata import AudioMetadataService
from services.audio.pipeline.normalization import AudioNormalizationService
from services.audio.pipeline.settings import AudioSettings
from services.audio.pipeline.temp_workspace import TempWorkspace
from services.audio.storage import AudioStorageService
from services.audio.utils.paths import resolve_media_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChapterResult:
    """One built chapter audio asset."""

    article_id: uuid.UUID
    audio_asset_id: uuid.UUID
    output_path: str
    duration_seconds: int
    segment_count: int


class ChapterAudioService:
    """Builds one MP3 per article chapter from segment audio."""

    def __init__(
        self,
        settings: AudioSettings | None = None,
        concatenation: AudioConcatenationService | None = None,
        normalization: AudioNormalizationService | None = None,
        export: AudioExportService | None = None,
        metadata: AudioMetadataService | None = None,
        storage: AudioStorageService | None = None,
    ) -> None:
        from infrastructure.media.ffmpeg_runner import FFmpegRunner, FFprobeRunner

        self._settings = settings or AudioSettings.from_django_settings()
        ffmpeg = FFmpegRunner(
            ffmpeg_binary=self._settings.ffmpeg_binary,
            timeout=self._settings.ffmpeg_timeout,
        )
        ffprobe = FFprobeRunner(ffprobe_binary=self._settings.ffprobe_binary)
        self._storage = storage or AudioStorageService(
            storage_subdir=self._settings.output_subdir,
        )
        self._normalization = normalization or AudioNormalizationService(
            ffmpeg,
            target_lufs=self._settings.target_lufs,
            enabled=self._settings.enable_normalization,
        )
        self._concatenation = concatenation or AudioConcatenationService(
            ffmpeg,
            silence_seconds=self._settings.default_silence_seconds,
            sample_rate=self._settings.default_sample_rate,
        )
        self._export = export or AudioExportService(
            ffmpeg,
            default_bitrate=self._settings.default_bitrate,
            default_sample_rate=self._settings.default_sample_rate,
        )
        self._metadata = metadata or AudioMetadataService(
            ffprobe=ffprobe,
            storage=self._storage,
        )

    def build_chapters(self, episode: Episode) -> list[ChapterResult]:
        """Build chapter MP3s for every article with linked segments.

        Returns an empty list (and logs) when segments carry no article
        links — e.g. single-article episodes or scripts generated before
        chaptered generation existed.
        """
        assets = list(
            AudioAsset.objects.filter(
                episode=episode,
                is_final_episode_audio=False,
                script_segment__isnull=False,
                status=AudioAssetStatus.READY,
            )
            .select_related("script_segment", "script_segment__article")
            .order_by("script_segment__sequence")
        )

        grouped: dict[uuid.UUID, list[AudioAsset]] = {}
        order: list[uuid.UUID] = []
        for asset in assets:
            article = asset.script_segment.article if asset.script_segment else None
            if article is None:
                continue
            if article.id not in grouped:
                grouped[article.id] = []
                order.append(article.id)
            grouped[article.id].append(asset)

        if not grouped:
            logger.info(
                "No article-linked segments; skipping chapter build",
                extra={
                    "event": "chapter_build_skipped",
                    "episode_id": str(episode.id),
                },
            )
            return []

        results: list[ChapterResult] = []
        with TempWorkspace(episode.id) as workspace:
            for position, article_id in enumerate(order, start=1):
                chapter_assets = grouped[article_id]
                results.append(
                    self._build_chapter(
                        episode,
                        article_id=article_id,
                        position=position,
                        assets=chapter_assets,
                        workspace=workspace,
                    )
                )

        logger.info(
            "Chapter audio built",
            extra={
                "event": "chapters_built",
                "episode_id": str(episode.id),
                "chapter_count": len(results),
            },
        )
        return results

    def _build_chapter(
        self,
        episode: Episode,
        *,
        article_id: uuid.UUID,
        position: int,
        assets: list[AudioAsset],
        workspace: TempWorkspace,
    ) -> ChapterResult:
        segment_paths = [
            resolve_media_path(asset.file_path, media_root=self._settings.media_root)
            for asset in assets
        ]
        chapter_dir = workspace.file(f"chapter_{position:02d}")
        chapter_dir.mkdir(parents=True, exist_ok=True)

        normalized = self._normalization.normalize_many(segment_paths, chapter_dir)
        concatenated = chapter_dir / "concatenated.wav"
        self._concatenation.concatenate(
            normalized,
            concatenated,
            workspace=chapter_dir,
        )

        output_path = self._chapter_output_path(episode.id, position)
        self._export.export_mp3(concatenated, output_path)

        metadata = self._metadata.calculate(output_path)
        asset = AudioAsset.objects.create(
            episode=episode,
            script_segment=None,
            article_id=article_id,
            provider="ffmpeg",
            file_path=self._storage.relative_path(output_path),
            duration=metadata.duration_seconds,
            sample_rate=metadata.sample_rate,
            bitrate=metadata.bitrate,
            format=metadata.format,
            file_size=metadata.file_size,
            checksum=metadata.checksum,
            status=AudioAssetStatus.READY,
            is_final_episode_audio=False,
            generated_at=timezone.now(),
        )
        return ChapterResult(
            article_id=article_id,
            audio_asset_id=asset.id,
            output_path=asset.file_path,
            duration_seconds=metadata.duration_seconds,
            segment_count=len(assets),
        )

    def _chapter_output_path(self, episode_id: uuid.UUID, position: int) -> Path:
        episode_dir = self._storage.root / str(episode_id)
        episode_dir.mkdir(parents=True, exist_ok=True)
        return episode_dir / f"chapter_{position:02d}.mp3"
