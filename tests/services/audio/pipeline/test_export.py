"""Tests for audio export service."""

from pathlib import Path

from services.audio.pipeline.export import AudioExportService
from tests.services.audio.pipeline.conftest import build_wav_file


def test_export_mp3(tmp_path: Path, ffmpeg_runner: object) -> None:
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.mp3"
    build_wav_file(input_path)
    service = AudioExportService(ffmpeg_runner)  # type: ignore[arg-type]
    result = service.export_mp3(input_path, output_path)
    assert result.exists()
    assert result.suffix == ".mp3"
