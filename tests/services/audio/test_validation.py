"""Tests for TTS validation."""

import pytest

from domain.audio.dtos import TTSRequest
from domain.audio.exceptions import (
    TTSException,
    UnsupportedFormatException,
    UnsupportedLanguageException,
    VoiceNotFoundException,
)
from infrastructure.audio.providers.tts.chatterbox import ChatterboxProvider
from services.audio.validation import TTSValidationService


@pytest.fixture
def validation_service(chatterbox_provider: ChatterboxProvider) -> TTSValidationService:
    return TTSValidationService(chatterbox_provider, max_text_length=100)


def test_validate_empty_text_raises(validation_service: TTSValidationService) -> None:
    with pytest.raises(TTSException, match="must not be empty"):
        validation_service.validate(TTSRequest(text="   "))


def test_validate_unsupported_format_raises(
    validation_service: TTSValidationService,
) -> None:
    with pytest.raises(UnsupportedFormatException):
        validation_service.validate(
            TTSRequest(text="Hello", output_format="flac", voice="expert.wav")
        )


def test_validate_unsupported_language_raises(
    validation_service: TTSValidationService,
) -> None:
    with pytest.raises(UnsupportedLanguageException):
        validation_service.validate(
            TTSRequest(text="Hello", language="jp", voice="expert.wav")
        )


def test_validate_unknown_voice_raises(
    validation_service: TTSValidationService,
) -> None:
    with pytest.raises(VoiceNotFoundException):
        validation_service.validate(
            TTSRequest(text="Hello", voice="missing.wav"),
            available_voice_ids={"expert.wav"},
        )
