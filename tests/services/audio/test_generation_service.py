"""Tests for audio generation service."""

from pathlib import Path
from unittest.mock import patch

import pytest

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import EpisodeStatus
from apps.scripts.models import ScriptStatus
from domain.audio.exceptions import (
    AudioGenerationException,
    ProviderUnavailableException,
)
from infrastructure.audio.providers.tts.chatterbox import ChatterboxProvider
from services.audio.generation_service import AudioGenerationService
from services.audio.storage import AudioStorageService
from services.audio.voice_cache import VoiceCacheService


@pytest.fixture
def audio_service(
    chatterbox_provider: ChatterboxProvider,
    tts_settings: object,
    tmp_path: Path,
) -> AudioGenerationService:
    storage = AudioStorageService(media_root=tmp_path, storage_subdir="audio")
    voice_cache = VoiceCacheService(chatterbox_provider, voice_ttl=60, health_ttl=60)
    return AudioGenerationService(
        provider=chatterbox_provider,
        settings=tts_settings,  # type: ignore[arg-type]
        storage_service=storage,
        voice_cache=voice_cache,
    )


def test_generate_for_script_creates_assets(
    audio_service: AudioGenerationService,
    ready_script: object,
    tmp_path: Path,
) -> None:
    results = audio_service.generate_for_script(ready_script)

    assert len(results) == 2
    assets = AudioAsset.objects.filter(episode=ready_script.episode)
    assert assets.count() == 2
    asset = assets.first()
    assert asset is not None
    assert asset.status == AudioAssetStatus.READY
    assert asset.provider == "chatterbox"
    assert asset.voice in {"Expert Voice", "Beginner Voice"}
    assert asset.sample_rate == 22050
    assert asset.format == "wav"
    assert asset.checksum
    assert asset.file_path.endswith(".wav")
    assert "segment_" in asset.file_path
    assert (tmp_path / asset.file_path).exists()

    ready_script.episode.refresh_from_db()
    assert ready_script.episode.status == EpisodeStatus.DRAFT


def test_generate_for_script_requires_ready_status(
    audio_service: AudioGenerationService,
    ready_script: object,
) -> None:
    ready_script.status = ScriptStatus.DRAFT
    ready_script.save(update_fields=["status"])
    with pytest.raises(AudioGenerationException, match="not ready"):
        audio_service.generate_for_script(ready_script)


def test_generate_fails_when_provider_unhealthy(
    audio_service: AudioGenerationService,
    ready_script: object,
) -> None:
    with (
        patch.object(audio_service._voice_cache, "is_healthy", return_value=False),
        pytest.raises(ProviderUnavailableException),
    ):
        audio_service.generate_for_script(ready_script)

    failed_assets = AudioAsset.objects.filter(status=AudioAssetStatus.FAILED)
    assert failed_assets.count() == 0
