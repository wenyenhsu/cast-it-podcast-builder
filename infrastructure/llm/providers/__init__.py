"""LLM provider adapters (lazy exports)."""

from infrastructure.llm.providers.base import BaseLLMProvider

__all__ = ["BaseLLMProvider", "OllamaProvider"]


def __getattr__(name: str) -> object:
    if name == "OllamaProvider":
        from infrastructure.llm.providers.ollama import OllamaProvider

        return OllamaProvider
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
