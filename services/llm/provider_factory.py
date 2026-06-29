"""Factory for creating LLM provider adapters."""

from domain.llm.exceptions import LLMException
from infrastructure.llm.providers.base import BaseLLMProvider
from infrastructure.llm.providers.ollama import HTTPClientProtocol, OllamaProvider
from services.llm.settings import LLMSettings


class LLMProviderFactory:
    """Creates LLM provider adapters based on application settings."""

    def __init__(self, settings: LLMSettings) -> None:
        self._settings = settings

    def create(
        self,
        http_client: HTTPClientProtocol | None = None,
    ) -> BaseLLMProvider:
        """Build a provider adapter for the configured backend."""
        provider = self._settings.provider.lower()

        if provider == "ollama":
            return OllamaProvider(
                config=self._settings.to_provider_config(),
                http_client=http_client,
            )

        raise LLMException(f"Unsupported LLM provider: {provider}")
