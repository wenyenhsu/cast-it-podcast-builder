"""Tests for TTS DTOs."""

from pathlib import Path

from domain.audio.dtos import TTSRequest, TTSResponse


def test_tts_request_defaults() -> None:
    request = TTSRequest(text="Hello world")
    assert request.language == "en"
    assert request.speed == 1.0
    assert request.output_format == "wav"


def test_tts_response_fields() -> None:
    response = TTSResponse(
        provider="chatterbox",
        voice="expert.wav",
        audio_file=Path("/tmp/test.wav"),
        duration=1.5,
        sample_rate=22050,
        format="wav",
        generation_time=0.42,
    )
    assert response.provider == "chatterbox"
    assert response.duration == 1.5
