"""Tests for pipeline audio validation."""

from pathlib import Path

import pytest

from domain.audio.pipeline_exceptions import AudioValidationError
from services.audio.pipeline.validation import AudioValidationService
from tests.services.audio.pipeline.conftest import build_wav_file


def test_validate_file_success(tmp_path: Path, ffprobe_runner: object) -> None:
    wav_path = tmp_path / "segment.wav"
    build_wav_file(wav_path)
    service = AudioValidationService(ffprobe=ffprobe_runner)  # type: ignore[arg-type]
    service.validate_file(wav_path)


def test_validate_missing_file(ffprobe_runner: object) -> None:
    service = AudioValidationService(ffprobe=ffprobe_runner)  # type: ignore[arg-type]
    with pytest.raises(AudioValidationError, match="does not exist"):
        service.validate_file(Path("/missing/file.wav"))


def test_validate_unsupported_extension(
    tmp_path: Path,
    ffprobe_runner: object,
) -> None:
    bad_path = tmp_path / "segment.txt"
    bad_path.write_text("not audio")
    service = AudioValidationService(ffprobe=ffprobe_runner)  # type: ignore[arg-type]
    with pytest.raises(AudioValidationError, match="Unsupported"):
        service.validate_file(bad_path)
