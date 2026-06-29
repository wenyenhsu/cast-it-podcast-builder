"""Factory for creating TTS provider adapters."""

from domain.audio.exceptions import TTSException
from infrastructure.audio.providers.tts.base import BaseTTSProvider
from infrastructure.audio.providers.tts.chatterbox import (
    ChatterboxProvider,
    HTTPClientProtocol,
)
from services.audio.settings import TTSSettings


class TTSProviderFactory:
    """Creates TTS provider adapters based on application settings."""

    def __init__(self, settings: TTSSettings) -> None:
        self._settings = settings

    def create(
        self,
        http_client: HTTPClientProtocol | None = None,
    ) -> BaseTTSProvider:
        """Build a provider adapter for the configured backend."""
        provider = self._settings.provider.lower()

        if provider == "chatterbox":
            return ChatterboxProvider(
                config=self._settings.to_provider_config(),
                http_client=http_client,
            )

        raise TTSException(f"Unsupported TTS provider: {provider}")
