"""Tests for audio storage service."""

from pathlib import Path

from services.audio.storage import AudioStorageService
from tests.services.audio.conftest import build_wav_bytes


def test_segment_path_and_save(tmp_path: Path) -> None:
    storage = AudioStorageService(media_root=tmp_path, storage_subdir="audio")
    source = tmp_path / "source.wav"
    source.write_bytes(build_wav_bytes())

    destination, checksum, file_size = storage.save_segment(
        source,
        episode_id="episode-123",
        sequence=1,
        output_format="wav",
    )

    assert destination.exists()
    assert checksum
    assert file_size > 0
    assert storage.relative_path(destination) == "audio/episode-123/segment_001.wav"
