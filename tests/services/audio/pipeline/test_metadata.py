"""Tests for audio metadata service."""

from pathlib import Path

from apps.audio.models import AudioAsset
from services.audio.pipeline.metadata import AudioMetadataService
from services.audio.storage import AudioStorageService
from tests.services.audio.pipeline.conftest import build_wav_file


def test_calculate_metadata(tmp_path: Path, ffprobe_runner: object) -> None:
    wav_path = tmp_path / "sample.wav"
    build_wav_file(wav_path)
    service = AudioMetadataService(ffprobe=ffprobe_runner)  # type: ignore[arg-type]
    metadata = service.calculate(wav_path)
    assert metadata.duration_seconds >= 1
    assert metadata.checksum
    assert metadata.sample_rate == 22050


def test_create_final_asset(
    episode_with_segments: object,
    tmp_path: Path,
    ffprobe_runner: object,
) -> None:
    media_root = episode_with_segments._test_media_root  # type: ignore[attr-defined]
    mp3_path = (
        media_root / "audio" / str(episode_with_segments.id) / "episode_final.mp3"
    )
    mp3_path.parent.mkdir(parents=True, exist_ok=True)
    mp3_path.write_bytes(b"ID3" + b"\x00" * 100)

    storage = AudioStorageService(media_root=media_root, storage_subdir="audio")
    service = AudioMetadataService(ffprobe=ffprobe_runner, storage=storage)  # type: ignore[arg-type]
    asset = service.create_final_asset(
        episode_id=episode_with_segments.id,
        absolute_path=mp3_path,
    )
    assert asset.is_final_episode_audio is True
    assert asset.script_segment_id is None
    assert AudioAsset.objects.filter(is_final_episode_audio=True).count() == 1
