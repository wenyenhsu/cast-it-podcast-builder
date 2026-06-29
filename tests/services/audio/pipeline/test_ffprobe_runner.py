"""Tests for FFprobe runner."""

from pathlib import Path

from infrastructure.media.ffmpeg_runner import FFprobeRunner
from tests.services.audio.pipeline.conftest import MockSubprocessRunner, build_wav_file


def test_ffprobe_runner_parses_metadata(
    tmp_path: Path,
    mock_runner: MockSubprocessRunner,
) -> None:
    wav_path = tmp_path / "sample.wav"
    build_wav_file(wav_path)
    runner = FFprobeRunner(ffprobe_binary="ffprobe", runner=mock_runner)
    result = runner.probe(wav_path)
    assert result.duration_seconds == 1.2
    assert result.sample_rate == 22050
    assert result.codec == "pcm_s16le"
