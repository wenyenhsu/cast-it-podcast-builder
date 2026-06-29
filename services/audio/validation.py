"""TTS request validation."""

import logging

from domain.audio.dtos import TTSRequest
from domain.audio.exceptions import (
    TTSException,
    UnsupportedFormatException,
    UnsupportedLanguageException,
    VoiceNotFoundException,
)
from infrastructure.audio.providers.tts.base import BaseTTSProvider

logger = logging.getLogger(__name__)


class TTSValidationService:
    """Validates TTS requests before provider calls."""

    def __init__(
        self,
        provider: BaseTTSProvider,
        *,
        max_text_length: int = 5000,
    ) -> None:
        self._provider = provider
        self._max_text_length = max_text_length

    def validate(
        self,
        request: TTSRequest,
        *,
        available_voice_ids: set[str] | None = None,
    ) -> None:
        """Validate a TTS request and raise on failure."""
        if not request.text.strip():
            raise TTSException("TTS text must not be empty.")

        if len(request.text) > self._max_text_length:
            raise TTSException(
                f"TTS text exceeds maximum length of "
                f"{self._max_text_length} characters."
            )

        output_format = request.output_format.lower().lstrip(".")
        supported_formats = {fmt.lower() for fmt in self._provider.supported_formats()}
        if output_format not in supported_formats:
            raise UnsupportedFormatException(
                f"Unsupported audio format '{request.output_format}'. "
                f"Supported: {', '.join(sorted(supported_formats))}."
            )

        if request.language:
            supported_languages = {
                lang.lower() for lang in self._provider.supported_languages()
            }
            if request.language.lower() not in supported_languages:
                raise UnsupportedLanguageException(
                    f"Unsupported language '{request.language}'. "
                    f"Supported: {', '.join(sorted(supported_languages))}."
                )

        if (
            request.voice
            and available_voice_ids is not None
            and request.voice not in available_voice_ids
        ):
            raise VoiceNotFoundException(
                f"Voice '{request.voice}' is not available for provider "
                f"{self._provider.provider_name}."
            )

        logger.debug(
            "TTS request validated",
            extra={
                "event": "tts_request_validated",
                "provider": self._provider.provider_name,
                "text_length": len(request.text),
            },
        )
