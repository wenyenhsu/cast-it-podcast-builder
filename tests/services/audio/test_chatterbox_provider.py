"""Tests for Chatterbox TTS provider."""

import pytest

from domain.audio.dtos import TTSRequest
from domain.audio.exceptions import ProviderUnavailableException, VoiceNotFoundException
from infrastructure.audio.providers.tts.chatterbox import ChatterboxProvider
from tests.services.audio.conftest import MockHTTPClient, MockHTTPResponse


def test_generate_segment_returns_normalized_response(
    chatterbox_provider: ChatterboxProvider,
    mock_http_client: MockHTTPClient,
) -> None:
    request = TTSRequest(
        text="Hello from the podcast.",
        voice="expert.wav",
        language="en",
        speed=1.0,
        output_format="wav",
    )
    response = chatterbox_provider.generate_segment(request)

    assert response.provider == "chatterbox"
    assert response.voice == "expert.wav"
    assert response.format == "wav"
    assert response.duration > 0
    assert response.sample_rate == 22050
    assert response.audio_file.exists()
    assert len(mock_http_client.post_calls) == 1


def test_generate_segment_voice_not_found(
    chatterbox_provider: ChatterboxProvider,
    mock_http_client: MockHTTPClient,
) -> None:
    mock_http_client.post = (
        lambda url, *, json, timeout: MockHTTPResponse(  # noqa: ARG005
            status_code=404,
            text="voice missing",
        )
    )
    with pytest.raises(VoiceNotFoundException):
        chatterbox_provider.generate_segment(
            TTSRequest(text="Hello", voice="missing.wav")
        )


def test_list_voices(chatterbox_provider: ChatterboxProvider) -> None:
    voices = chatterbox_provider.list_voices()
    assert len(voices) == 2
    assert voices[0].voice_id == "expert.wav"


def test_health_check(chatterbox_provider: ChatterboxProvider) -> None:
    assert chatterbox_provider.health_check() is True


def test_supported_languages(chatterbox_provider: ChatterboxProvider) -> None:
    assert chatterbox_provider.supported_languages() == ["en", "es"]


def test_estimate_duration(chatterbox_provider: ChatterboxProvider) -> None:
    duration = chatterbox_provider.estimate_duration("one two three four five six")
    assert duration > 0


def test_provider_unavailable_on_network_error(
    tts_config: object,
    tmp_path: object,
) -> None:
    client = MockHTTPClient()
    client.post = lambda *args, **kwargs: (_ for _ in ()).throw(  # noqa: ARG005
        ConnectionError("down")
    )
    provider = ChatterboxProvider(
        config=tts_config,  # type: ignore[arg-type]
        http_client=client,
        temp_dir=tmp_path,  # type: ignore[arg-type]
    )
    with pytest.raises(ProviderUnavailableException):
        provider.generate_segment(TTSRequest(text="Hello", voice="expert.wav"))
