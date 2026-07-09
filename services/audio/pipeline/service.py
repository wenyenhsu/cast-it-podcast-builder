"""Audio post-processing pipeline orchestration service."""

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode, EpisodeStatus
from domain.audio.pipeline_exceptions import (
    AudioPipelineError,
    MissingAudioAssetError,
)
from infrastructure.media.ffmpeg_runner import FFmpegRunner, FFprobeRunner
from services.audio.pipeline.concatenation import AudioConcatenationService
from services.audio.pipeline.export import AudioExportService
from services.audio.pipeline.metadata import AudioMetadataService
from services.audio.pipeline.normalization import AudioNormalizationService
from services.audio.pipeline.settings import AudioSettings
from services.audio.pipeline.temp_workspace import TempWorkspace
from services.audio.pipeline.validation import AudioValidationService
from services.audio.storage import AudioStorageService
from services.audio.utils.paths import resolve_media_path

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineResult:
    """Result of a completed audio pipeline run."""

    episode_id: uuid.UUID
    audio_asset_id: uuid.UUID
    output_path: str
    duration_seconds: int
    segment_count: int
    processing_time_seconds: float


class AudioPipelineService:
    """Builds and executes the episode audio post-processing pipeline."""

    def __init__(
        self,
        settings: AudioSettings | None = None,
        ffmpeg: FFmpegRunner | None = None,
        ffprobe: FFprobeRunner | None = None,
        validation: AudioValidationService | None = None,
        normalization: AudioNormalizationService | None = None,
        concatenation: AudioConcatenationService | None = None,
        export: AudioExportService | None = None,
        metadata: AudioMetadataService | None = None,
        storage: AudioStorageService | None = None,
    ) -> None:
        self._settings = settings or AudioSettings.from_django_settings()
        self._ffmpeg = ffmpeg or FFmpegRunner(
            ffmpeg_binary=self._settings.ffmpeg_binary,
            timeout=self._settings.ffmpeg_timeout,
        )
        self._ffprobe = ffprobe or FFprobeRunner(
            ffprobe_binary=self._settings.ffprobe_binary,
        )
        self._storage = storage or AudioStorageService(
            storage_subdir=self._settings.output_subdir,
        )
        self._validation = validation or AudioValidationService(ffprobe=self._ffprobe)
        self._normalization = normalization or AudioNormalizationService(
            self._ffmpeg,
            target_lufs=self._settings.target_lufs,
            enabled=self._settings.enable_normalization,
        )
        self._concatenation = concatenation or AudioConcatenationService(
            self._ffmpeg,
            silence_seconds=self._settings.default_silence_seconds,
            sample_rate=self._settings.default_sample_rate,
        )
        self._export = export or AudioExportService(
            self._ffmpeg,
            default_bitrate=self._settings.default_bitrate,
            default_sample_rate=self._settings.default_sample_rate,
        )
        self._metadata = metadata or AudioMetadataService(
            ffprobe=self._ffprobe,
            storage=self._storage,
        )

    def process_episode(self, episode: Episode) -> PipelineResult:
        """Run the full audio pipeline for an episode."""
        started = time.perf_counter()
        logger.info(
            "Audio pipeline started",
            extra={
                "event": "audio_pipeline_started",
                "episode_id": str(episode.id),
            },
        )

        try:
            result = self._run_pipeline(episode)
        except AudioPipelineError as exc:
            episode.status = EpisodeStatus.FAILED
            episode.save(update_fields=["status", "updated_at"])
            logger.error(
                "Audio pipeline failed",
                extra={
                    "event": "audio_pipeline_failed",
                    "episode_id": str(episode.id),
                    "error": str(exc),
                },
            )
            raise
        except Exception as exc:
            episode.status = EpisodeStatus.FAILED
            episode.save(update_fields=["status", "updated_at"])
            logger.exception(
                "Audio pipeline failed unexpectedly",
                extra={
                    "event": "audio_pipeline_error",
                    "episode_id": str(episode.id),
                },
            )
            raise AudioPipelineError(str(exc)) from exc

        elapsed = time.perf_counter() - started
        logger.info(
            "Audio pipeline completed",
            extra={
                "event": "audio_pipeline_completed",
                "episode_id": str(episode.id),
                "output_path": result.output_path,
                "duration_seconds": result.duration_seconds,
                "processing_time_seconds": round(elapsed, 3),
            },
        )
        result = PipelineResult(
            episode_id=result.episode_id,
            audio_asset_id=result.audio_asset_id,
            output_path=result.output_path,
            duration_seconds=result.duration_seconds,
            segment_count=result.segment_count,
            processing_time_seconds=round(elapsed, 3),
        )
        return result

    @transaction.atomic
    def _run_pipeline(self, episode: Episode) -> PipelineResult:
        assets = self._load_segment_assets(episode)
        resolved_paths = [
            resolve_media_path(asset.file_path, media_root=self._settings.media_root)
            for asset in assets
        ]

        intro_path = self._settings.resolve_optional_path(
            self._settings.intro_file_path
        )
        outro_path = self._settings.resolve_optional_path(
            self._settings.outro_file_path
        )
        music_path = (
            self._settings.resolve_optional_path(self._settings.background_music_path)
            if self._settings.enable_background_music
            else None
        )

        self._validation.validate_assets(assets, resolved_paths)
        self._validation.validate_optional_file(intro_path, "Intro")
        self._validation.validate_optional_file(outro_path, "Outro")
        self._validation.validate_optional_file(music_path, "Background music")

        with TempWorkspace(episode.id) as workspace:
            logger.info(
                "Pipeline stage: normalization",
                extra={
                    "event": "audio_pipeline_stage",
                    "stage": "normalization",
                    "episode_id": str(episode.id),
                    "segment_count": len(resolved_paths),
                },
            )
            normalized_paths = self._normalization.normalize_many(
                resolved_paths,
                workspace.path,
            )

            concatenated_path = workspace.file("concatenated.wav")
            logger.info(
                "Pipeline stage: concatenation",
                extra={
                    "event": "audio_pipeline_stage",
                    "stage": "concatenation",
                    "episode_id": str(episode.id),
                },
            )
            self._concatenation.concatenate(
                normalized_paths,
                concatenated_path,
                workspace=workspace.path,
                intro_path=intro_path,
                outro_path=outro_path,
            )

            mixed_path = concatenated_path
            if music_path is not None:
                mixed_path = workspace.file("mixed.wav")
                logger.info(
                    "Pipeline stage: background_music",
                    extra={
                        "event": "audio_pipeline_stage",
                        "stage": "background_music",
                        "episode_id": str(episode.id),
                    },
                )
                self._concatenation.mix_background_music(
                    concatenated_path,
                    music_path,
                    mixed_path,
                    music_volume=self._settings.background_music_volume,
                )

            final_mp3_path = self._final_output_path(episode.id)
            logger.info(
                "Pipeline stage: export",
                extra={
                    "event": "audio_pipeline_stage",
                    "stage": "export",
                    "episode_id": str(episode.id),
                    "output_path": str(final_mp3_path),
                },
            )
            self._export.export_mp3(mixed_path, final_mp3_path)

        asset = self._metadata.create_final_asset(
            episode_id=episode.id,
            absolute_path=final_mp3_path,
        )

        from services.audio.pipeline.chapters import ChapterAudioService

        ChapterAudioService(settings=self._settings).build_chapters(episode)

        episode.status = EpisodeStatus.COMPLETED
        episode.duration_seconds = asset.duration
        episode.save(update_fields=["status", "duration_seconds", "updated_at"])

        return PipelineResult(
            episode_id=episode.id,
            audio_asset_id=asset.id,
            output_path=asset.file_path,
            duration_seconds=asset.duration or 0,
            segment_count=len(assets),
            processing_time_seconds=0.0,
        )

    def _load_segment_assets(self, episode: Episode) -> list[AudioAsset]:
        assets = list(
            AudioAsset.objects.filter(
                episode=episode,
                is_final_episode_audio=False,
                script_segment__isnull=False,
                status=AudioAssetStatus.READY,
            )
            .select_related("script_segment")
            .order_by("script_segment__sequence")
        )
        if not assets:
            raise MissingAudioAssetError(
                f"No ready segment audio assets found for episode {episode.id}."
            )
        return assets

    def _final_output_path(self, episode_id: uuid.UUID) -> Path:
        episode_dir = self._storage.root / str(episode_id)
        episode_dir.mkdir(parents=True, exist_ok=True)
        return episode_dir / "episode_final.mp3"
