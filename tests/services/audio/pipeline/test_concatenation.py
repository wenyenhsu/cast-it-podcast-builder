"""Tests for audio concatenation service."""

from pathlib import Path

from services.audio.pipeline.concatenation import AudioConcatenationService
from tests.services.audio.pipeline.conftest import build_wav_file


def test_concatenate_segments(
    tmp_path: Path,
    ffmpeg_runner: object,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    segments = []
    for index in range(2):
        path = workspace / f"seg_{index}.wav"
        build_wav_file(path)
        segments.append(path)

    output_path = workspace / "combined.wav"
    service = AudioConcatenationService(
        ffmpeg_runner,  # type: ignore[arg-type]
        silence_seconds=0.5,
    )
    result = service.concatenate(
        segments,
        output_path,
        workspace=workspace,
    )
    assert result.exists()


def test_mix_background_music(
    tmp_path: Path,
    ffmpeg_runner: object,
) -> None:
    speech = tmp_path / "speech.wav"
    music = tmp_path / "music.wav"
    output = tmp_path / "mixed.wav"
    build_wav_file(speech)
    build_wav_file(music)

    service = AudioConcatenationService(ffmpeg_runner)  # type: ignore[arg-type]
    result = service.mix_background_music(speech, music, output)
    assert result.exists()
