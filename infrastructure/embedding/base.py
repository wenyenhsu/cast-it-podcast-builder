"""Abstract embedding provider interface."""

from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Provider-agnostic embedding generation abstraction."""

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the embedding provider is healthy."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the active embedding model name."""
