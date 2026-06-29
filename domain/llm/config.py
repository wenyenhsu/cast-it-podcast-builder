"""LLM provider configuration."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LLMProviderConfig:
    """Provider-agnostic configuration passed to LLM adapters."""

    base_url: str
    chat_model: str
    embedding_model: str
    temperature: float
    timeout: float
