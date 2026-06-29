"""Tests for FFmpeg runner."""

import subprocess

import pytest

from domain.audio.pipeline_exceptions import FFmpegExecutionError
from infrastructure.media.ffmpeg_runner import FFmpegRunner
from tests.services.audio.pipeline.conftest import MockSubprocessRunner


def test_ffmpeg_runner_success(mock_runner: MockSubprocessRunner) -> None:
    runner = FFmpegRunner(ffmpeg_binary="ffmpeg", runner=mock_runner)
    result = runner.run(["-version"])
    assert result.returncode == 0
    assert len(mock_runner.calls) == 1


def test_ffmpeg_runner_failure() -> None:
    class FailingRunner:
        def run(
            self,
            args: list[str],
            *,
            capture_output: bool,
            text: bool,
            timeout: float,
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="error",
            )

    runner = FFmpegRunner(ffmpeg_binary="ffmpeg", runner=FailingRunner())
    with pytest.raises(FFmpegExecutionError, match="FFmpeg failed"):
        runner.run(["-i", "input.wav", "output.wav"])
