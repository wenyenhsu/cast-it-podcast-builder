"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from collections.abc import Iterator

from domain.llm.dtos import EmbeddingResponse, LLMRequest, LLMResponse, ModelInfo


class BaseLLMProvider(ABC):
    """Abstract adapter that every LLM provider must implement."""

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion from a single prompt."""

    @abstractmethod
    def chat(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion using a chat-style message format."""

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Stream completion tokens as they are generated."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the provider is reachable and the configured model exists."""

    @abstractmethod
    def list_models(self) -> list[ModelInfo]:
        """Return normalized metadata for available models."""

    @abstractmethod
    def embed(self, text: str) -> EmbeddingResponse:
        """Return a normalized embedding vector for the given text."""
