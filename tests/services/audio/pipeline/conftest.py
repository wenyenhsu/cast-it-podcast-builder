"""Shared fixtures for audio pipeline tests."""

import json
import subprocess
import wave
from pathlib import Path

import pytest
from django.utils import timezone

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptSegment, ScriptStatus, Speaker
from infrastructure.media.ffmpeg_runner import FFmpegRunner, FFprobeRunner
from services.audio.pipeline.settings import AudioSettings


def build_wav_file(path: Path, *, duration_seconds: float = 0.5) -> None:
    """Write a minimal WAV file to disk."""
    sample_rate = 22050
    frame_count = int(sample_rate * duration_seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)


def build_probe_json(*, duration: float = 1.0) -> str:
    return json.dumps(
        {
            "format": {
                "duration": str(duration),
                "format_name": "wav",
                "bit_rate": "128000",
            },
            "streams": [
                {
                    "codec_type": "audio",
                    "codec_name": "pcm_s16le",
                    "sample_rate": "22050",
                }
            ],
        }
    )


class MockSubprocessRunner:
    """Mock subprocess runner for FFmpeg and FFprobe tests."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def run(
        self,
        args: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, timeout
        self.calls.append(args)
        binary = args[0]

        if "ffprobe" in binary:
            return subprocess.CompletedProcess(
                args=args,
                returncode=0,
                stdout=build_probe_json(duration=1.2),
                stderr="",
            )

        output_path = Path(args[-1])
        if output_path.suffix == ".mp3":
            output_path.write_bytes(b"ID3" + b"\x00" * 100)
        else:
            build_wav_file(output_path, duration_seconds=0.5)

        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="",
        )


@pytest.fixture
def mock_runner() -> MockSubprocessRunner:
    return MockSubprocessRunner()


@pytest.fixture
def ffmpeg_runner(mock_runner: MockSubprocessRunner) -> FFmpegRunner:
    return FFmpegRunner(ffmpeg_binary="ffmpeg", runner=mock_runner)


@pytest.fixture
def ffprobe_runner(mock_runner: MockSubprocessRunner) -> FFprobeRunner:
    return FFprobeRunner(ffprobe_binary="ffprobe", runner=mock_runner)


@pytest.fixture
def audio_settings(tmp_path: Path) -> AudioSettings:
    intro = tmp_path / "intro.wav"
    outro = tmp_path / "outro.wav"
    build_wav_file(intro)
    build_wav_file(outro)
    return AudioSettings(
        output_subdir="audio",
        default_bitrate=192,
        default_sample_rate=44100,
        default_silence_seconds=0.5,
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


@pytest.fixture
def episode_with_segments(db: None, tmp_path: Path) -> Episode:
    media_root = tmp_path / "media"
    episode = Episode.objects.create(
        title="Pipeline Episode",
        summary="Test episode",
        language="en",
        status=EpisodeStatus.GENERATING_AUDIO,
    )
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Script",
        status=ScriptStatus.READY,
    )
    for sequence, speaker in ((1, Speaker.EXPERT), (2, Speaker.BEGINNER)):
        segment = ScriptSegment.objects.create(
            script=script,
            sequence=sequence,
            speaker=speaker,
            text=f"Segment {sequence} text.",
        )
        wav_path = (
            media_root / "audio" / str(episode.id) / f"segment_{sequence:03d}.wav"
        )
        build_wav_file(wav_path)
        AudioAsset.objects.create(
            episode=episode,
            script_segment=segment,
            provider="chatterbox",
            voice="test-voice",
            file_path=str(wav_path.relative_to(media_root)),
            duration=1,
            format="wav",
            sample_rate=22050,
            status=AudioAssetStatus.READY,
            is_final_episode_audio=False,
            generated_at=timezone.now(),
        )
    episode._test_media_root = media_root  # type: ignore[attr-defined]
    return episode
