"""Tests for audio pipeline service."""

from pathlib import Path

import pytest
from django.conf import settings as django_settings

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import EpisodeStatus
from domain.audio.pipeline_exceptions import MissingAudioAssetError
from services.audio.pipeline.service import AudioPipelineService
from services.audio.pipeline.settings import AudioSettings
from services.audio.storage import AudioStorageService


@pytest.fixture
def pipeline_service(
    episode_with_segments: object,
    audio_settings: AudioSettings,
    ffmpeg_runner: object,
    ffprobe_runner: object,
    tmp_path: Path,
) -> AudioPipelineService:
    media_root = episode_with_segments._test_media_root  # type: ignore[attr-defined]
    django_settings.MEDIA_ROOT = media_root

    intro = media_root / "intro.wav"
    outro = media_root / "outro.wav"
    from tests.services.audio.pipeline.conftest import build_wav_file

    build_wav_file(intro)
    build_wav_file(outro)

    pipeline_settings = AudioSettings(
        output_subdir="audio",
        default_bitrate=audio_settings.default_bitrate,
        default_sample_rate=audio_settings.default_sample_rate,
        default_silence_seconds=audio_settings.default_silence_seconds,
        intro_file_path=str(intro),
        outro_file_path=str(outro),
        background_music_path="",
        enable_background_music=False,
        enable_normalization=True,
        background_music_volume=0.15,
        ffmpeg_binary="ffmpeg",
        ffprobe_binary="ffprobe",
        ffmpeg_timeout=60.0,
        target_lufs=-16.0,
    )

    storage = AudioStorageService(media_root=media_root, storage_subdir="audio")
    return AudioPipelineService(
        settings=pipeline_settings,
        ffmpeg=ffmpeg_runner,  # type: ignore[arg-type]
        ffprobe=ffprobe_runner,  # type: ignore[arg-type]
        storage=storage,
    )


def test_process_episode_creates_final_mp3(
    pipeline_service: AudioPipelineService,
    episode_with_segments: object,
) -> None:
    media_root = episode_with_segments._test_media_root  # type: ignore[attr-defined]
    result = pipeline_service.process_episode(episode_with_segments)

    assert result.segment_count == 2
    assert result.duration_seconds >= 1
    final_asset = AudioAsset.objects.get(is_final_episode_audio=True)
    assert final_asset.status == AudioAssetStatus.READY
    assert final_asset.format == "mp3"
    assert (media_root / final_asset.file_path).exists()

    episode_with_segments.refresh_from_db()
    assert episode_with_segments.status == EpisodeStatus.COMPLETED
    assert episode_with_segments.duration_seconds == final_asset.duration


def test_process_episode_missing_assets(
    pipeline_service: AudioPipelineService,
    episode_with_segments: object,
) -> None:
    AudioAsset.objects.filter(episode=episode_with_segments).delete()
    with pytest.raises(MissingAudioAssetError):
        pipeline_service.process_episode(episode_with_segments)

    episode_with_segments.refresh_from_db()
    assert episode_with_segments.status == EpisodeStatus.FAILED
