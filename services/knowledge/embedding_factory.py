"""Factory for embedding providers."""

from infrastructure.embedding.base import BaseEmbeddingProvider
from infrastructure.embedding.ollama import OllamaEmbeddingProvider
from services.llm.settings import LLMSettings


class EmbeddingProviderFactory:
    """Creates embedding providers based on LLM configuration."""

    def __init__(self, llm_settings: LLMSettings | None = None) -> None:
        self._llm_settings = llm_settings or LLMSettings.from_django_settings()

    def create(self) -> BaseEmbeddingProvider:
        provider = self._llm_settings.provider.lower()
        if provider == "ollama":
            return OllamaEmbeddingProvider(self._llm_settings.to_provider_config())
        raise ValueError(f"Unsupported embedding provider: {provider}")
