"""Ollama embedding provider adapter."""

import logging

from domain.llm.config import LLMProviderConfig
from domain.llm.exceptions import LLMException
from infrastructure.embedding.base import BaseEmbeddingProvider
from infrastructure.llm.providers.ollama import OllamaProvider

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Generates embeddings through the Ollama HTTP API."""

    def __init__(
        self,
        config: LLMProviderConfig,
        provider: OllamaProvider | None = None,
    ) -> None:
        self._config = config
        self._provider = provider or OllamaProvider(config)

    @property
    def model_name(self) -> str:
        return self._config.embedding_model

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise LLMException("Embedding input must not be empty.")
        response = self._provider.embed(text)
        return response.embedding

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return [self.embed(text) for text in texts]

    def health_check(self) -> bool:
        healthy = self._provider.health_check()
        if not healthy:
            logger.warning(
                "Embedding provider health check failed",
                extra={
                    "event": "embedding_provider_health_failed",
                    "provider": "ollama",
                    "model": self.model_name,
                },
            )
        return healthy
