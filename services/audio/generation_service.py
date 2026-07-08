"""Segment audio generation orchestration service."""

import logging
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import EpisodeStatus
from apps.scripts.models import Script, ScriptSegment, ScriptStatus
from domain.audio.dtos import TTSRequest, TTSResponse
from domain.audio.exceptions import (
    AudioGenerationException,
    ProviderUnavailableException,
    TTSException,
)
from infrastructure.audio.providers.tts.base import BaseTTSProvider
from services.audio.persona_resolver import PersonaVoiceResolver
from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings
from services.audio.storage import AudioStorageService
from services.audio.validation import TTSValidationService
from services.audio.voice_cache import VoiceCacheService
from services.episodes.status_sync import sync_episode_idle_status

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SegmentAudioResult:
    """Reference to a generated segment audio asset."""

    segment_id: uuid.UUID
    audio_asset_id: uuid.UUID
    file_path: str
    duration: float


class AudioGenerationService:
    """Generates individual audio assets for script segments."""

    def __init__(
        self,
        provider: BaseTTSProvider | None = None,
        settings: TTSSettings | None = None,
        persona_resolver: PersonaVoiceResolver | None = None,
        storage_service: AudioStorageService | None = None,
        voice_cache: VoiceCacheService | None = None,
    ) -> None:
        self._settings = settings or TTSSettings.from_django_settings()
        self._provider = provider or TTSProviderFactory(self._settings).create()
        self._persona_resolver = persona_resolver or PersonaVoiceResolver()
        self._storage = storage_service or AudioStorageService(
            storage_subdir=self._settings.storage_subdir,
        )
        self._voice_cache = voice_cache or VoiceCacheService(self._provider)
        self._validation = TTSValidationService(
            self._provider,
            max_text_length=self._settings.max_text_length,
        )

    @property
    def provider(self) -> BaseTTSProvider:
        return self._provider

    def generate_for_script(self, script: Script) -> list[SegmentAudioResult]:
        """Generate audio for all segments in a script."""
        from services.audio.voice_setup import VoiceSetupService

        VoiceSetupService().ensure_defaults(self._settings)

        if script.status not in {ScriptStatus.READY, ScriptStatus.APPROVED}:
            raise AudioGenerationException(
                f"Script {script.id} is not ready for audio generation."
            )

        episode = script.episode
        episode.status = EpisodeStatus.GENERATING_AUDIO
        episode.save(update_fields=["status", "updated_at"])

        if not self._voice_cache.is_healthy():
            raise ProviderUnavailableException(
                f"TTS provider '{self._provider.provider_name}' is unavailable."
            )

        available_voices = self._voice_cache.get_voice_ids()
        segments = list(script.segments.order_by("sequence"))
        results: list[SegmentAudioResult] = []

        logger.info(
            "Audio generation started",
            extra={
                "event": "audio_generation_started",
                "script_id": str(script.id),
                "episode_id": str(episode.id),
                "segment_count": len(segments),
                "provider": self._provider.provider_name,
            },
        )

        started = time.perf_counter()
        for segment in segments:
            result = self._generate_segment(
                segment=segment,
                episode_id=episode.id,
                language=episode.language,
                available_voices=available_voices,
            )
            results.append(result)

        elapsed = time.perf_counter() - started
        logger.info(
            "Audio generation completed",
            extra={
                "event": "audio_generation_completed",
                "script_id": str(script.id),
                "episode_id": str(episode.id),
                "segment_count": len(results),
                "generation_time_seconds": round(elapsed, 3),
            },
        )
        sync_episode_idle_status(episode)
        return results

    def generate_segment(self, segment: ScriptSegment) -> SegmentAudioResult:
        """Generate audio for a single script segment."""
        episode = segment.script.episode
        if not self._voice_cache.is_healthy():
            raise ProviderUnavailableException(
                f"TTS provider '{self._provider.provider_name}' is unavailable."
            )

        available_voices = self._voice_cache.get_voice_ids()
        return self._generate_segment(
            segment=segment,
            episode_id=episode.id,
            language=episode.language,
            available_voices=available_voices,
        )

    @transaction.atomic
    def _generate_segment(
        self,
        *,
        segment: ScriptSegment,
        episode_id: uuid.UUID,
        language: str,
        available_voices: set[str],
    ) -> SegmentAudioResult:
        voice_profile = self._persona_resolver.resolve_for_episode_language(
            segment.speaker,
            provider=self._provider.provider_name,
            episode_id=episode_id,
            language=language,
        )

        tts_request = TTSRequest(
            text=segment.text,
            speaker=segment.speaker,
            voice=voice_profile.provider_voice_id,
            emotion=segment.emotion,
            language=language,
            speed=voice_profile.default_speed,
            output_format=self._settings.audio_format,
        )

        self._validation.validate(
            tts_request,
            available_voice_ids=available_voices or None,
        )

        asset = AudioAsset.objects.create(
            episode_id=episode_id,
            script_segment=segment,
            provider=self._provider.provider_name,
            voice=voice_profile.name,
            file_path="",
            status=AudioAssetStatus.GENERATING,
        )

        response: TTSResponse | None = None
        try:
            response = self._provider.generate_segment(tts_request)
            asset = self._persist_asset(
                asset=asset,
                response=response,
                episode_id=episode_id,
                sequence=segment.sequence,
                voice_profile_name=voice_profile.name,
            )
        except TTSException as exc:
            asset.status = AudioAssetStatus.FAILED
            asset.save(update_fields=["status", "updated_at"])
            logger.error(
                "Segment audio generation failed",
                extra={
                    "event": "segment_audio_generation_failed",
                    "segment_id": str(segment.id),
                    "episode_id": str(episode_id),
                    "error": str(exc),
                },
            )
            raise AudioGenerationException(str(exc)) from exc
        finally:
            if response is not None:
                self._cleanup_temp_file(response.audio_file)

        logger.info(
            "Segment audio generated",
            extra={
                "event": "segment_audio_generated",
                "segment_id": str(segment.id),
                "episode_id": str(episode_id),
                "audio_asset_id": str(asset.id),
                "provider": self._provider.provider_name,
                "speaker": segment.speaker,
                "provider_voice_id": voice_profile.provider_voice_id,
                "voice": voice_profile.name,
                "duration": asset.duration,
                "generation_time": asset.generation_time,
            },
        )

        return SegmentAudioResult(
            segment_id=segment.id,
            audio_asset_id=asset.id,
            file_path=asset.file_path,
            duration=float(asset.duration or 0),
        )

    def _persist_asset(
        self,
        *,
        asset: AudioAsset,
        response: TTSResponse,
        episode_id: uuid.UUID,
        sequence: int,
        voice_profile_name: str,
    ) -> AudioAsset:
        destination, checksum, file_size = self._storage.save_segment(
            response.audio_file,
            episode_id,
            sequence,
            output_format=response.format,
        )
        relative_path = self._storage.relative_path(destination)

        asset.provider = response.provider
        asset.voice = voice_profile_name
        asset.file_path = relative_path
        asset.duration = max(1, int(round(response.duration)))
        asset.sample_rate = response.sample_rate
        asset.bitrate = response.bitrate
        asset.format = response.format
        asset.generation_time = response.generation_time
        asset.checksum = checksum
        asset.file_size = file_size
        asset.status = AudioAssetStatus.READY
        asset.generated_at = timezone.now()
        asset.save(
            update_fields=[
                "provider",
                "voice",
                "file_path",
                "duration",
                "sample_rate",
                "bitrate",
                "format",
                "generation_time",
                "checksum",
                "file_size",
                "status",
                "generated_at",
                "updated_at",
            ]
        )
        return asset

    @staticmethod
    def _cleanup_temp_file(path: Path | None) -> None:
        if path is not None and path.exists():
            path.unlink(missing_ok=True)
