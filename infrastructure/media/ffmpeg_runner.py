"""FFmpeg and FFprobe subprocess runners."""

import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from domain.audio.pipeline_exceptions import FFmpegExecutionError

logger = logging.getLogger(__name__)

DEFAULT_FFMPEG_TIMEOUT = 300.0
DEFAULT_FFPROBE_TIMEOUT = 60.0


class SubprocessRunner(Protocol):
    """Protocol for the subprocess execution dependency."""

    def run(
        self,
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]: ...


class _DefaultSubprocessRunner:
    """Executes commands with the standard library subprocess module."""

    def run(
        self,
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            capture_output=capture_output,
            text=text,
            timeout=timeout,
            check=False,
        )


@dataclass(frozen=True)
class FFmpegResult:
    """Outcome of a completed FFmpeg invocation."""

    returncode: int
    stdout: str
    stderr: str
    elapsed_time: float


@dataclass(frozen=True)
class ProbeResult:
    """Parsed FFprobe metadata for an audio file."""

    duration_seconds: float
    sample_rate: int
    codec: str
    bitrate: int | None
    format_name: str


class FFmpegRunner:
    """Runs FFmpeg commands and raises on failure."""

    def __init__(
        self,
        ffmpeg_binary: str = "ffmpeg",
        *,
        timeout: float = DEFAULT_FFMPEG_TIMEOUT,
        runner: SubprocessRunner | None = None,
    ) -> None:
        self._binary = ffmpeg_binary
        self._timeout = timeout
        self._runner = runner or _DefaultSubprocessRunner()

    def run(self, args: list[str]) -> FFmpegResult:
        """Execute FFmpeg with the given arguments (binary is prepended)."""
        full_args = [self._binary, *args]
        started = time.perf_counter()
        try:
            completed = self._runner.run(
                full_args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise FFmpegExecutionError(
                f"FFmpeg failed: timed out after {self._timeout}s"
            ) from exc
        elapsed = time.perf_counter() - started

        if completed.returncode != 0:
            stderr_tail = (completed.stderr or "")[-2000:]
            raise FFmpegExecutionError(
                f"FFmpeg failed (exit {completed.returncode}): {stderr_tail}"
            )

        return FFmpegResult(
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
            elapsed_time=elapsed,
        )


class FFprobeRunner:
    """Runs FFprobe and parses stream/format metadata."""

    def __init__(
        self,
        ffprobe_binary: str = "ffprobe",
        *,
        timeout: float = DEFAULT_FFPROBE_TIMEOUT,
        runner: SubprocessRunner | None = None,
    ) -> None:
        self._binary = ffprobe_binary
        self._timeout = timeout
        self._runner = runner or _DefaultSubprocessRunner()

    def probe(self, file_path: Path) -> ProbeResult:
        """Return parsed metadata for the given media file."""
        args = [
            self._binary,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ]
        try:
            completed = self._runner.run(
                args,
                capture_output=True,
                text=True,
                timeout=self._timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise FFmpegExecutionError(
                f"FFprobe failed: timed out after {self._timeout}s"
            ) from exc

        if completed.returncode != 0:
            stderr_tail = (completed.stderr or "")[-2000:]
            raise FFmpegExecutionError(
                f"FFprobe failed (exit {completed.returncode}): {stderr_tail}"
            )

        data = json.loads(completed.stdout or "{}")
        format_info = data.get("format", {})
        audio_stream = next(
            (
                stream
                for stream in data.get("streams", [])
                if stream.get("codec_type") == "audio"
            ),
            {},
        )

        duration_raw = format_info.get("duration") or audio_stream.get("duration")
        bit_rate_raw = format_info.get("bit_rate")

        return ProbeResult(
            duration_seconds=float(duration_raw) if duration_raw else 0.0,
            sample_rate=int(audio_stream.get("sample_rate") or 0),
            codec=audio_stream.get("codec_name") or "",
            bitrate=int(bit_rate_raw) if bit_rate_raw else None,
            format_name=(format_info.get("format_name") or "").split(",")[0],
        )
