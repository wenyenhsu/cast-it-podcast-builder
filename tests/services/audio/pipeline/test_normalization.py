"""Tests for audio normalization service."""

from pathlib import Path

from services.audio.pipeline.normalization import AudioNormalizationService
from tests.services.audio.pipeline.conftest import build_wav_file


def test_normalize_writes_output(
    tmp_path: Path,
    ffmpeg_runner: object,
) -> None:
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    build_wav_file(input_path)
    service = AudioNormalizationService(ffmpeg_runner)  # type: ignore[arg-type]
    result = service.normalize(input_path, output_path)
    assert result.exists()


def test_normalize_disabled_copies_file(tmp_path: Path, ffmpeg_runner: object) -> None:
    input_path = tmp_path / "input.wav"
    output_path = tmp_path / "output.wav"
    build_wav_file(input_path)
    service = AudioNormalizationService(
        ffmpeg_runner,  # type: ignore[arg-type]
        enabled=False,
    )
    service.normalize(input_path, output_path)
    assert output_path.read_bytes() == input_path.read_bytes()
