"""LLM request and response data transfer objects."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class LLMRequest:
    """Normalized request payload for LLM providers."""

    system_prompt: str = ""
    user_prompt: str = ""
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    json_mode: bool = False
    json_schema: dict[str, Any] | None = None


@dataclass(frozen=True)
class LLMResponse:
    """Normalized response from an LLM provider."""

    content: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = ""
    elapsed_time: float = 0.0


@dataclass(frozen=True)
class EmbeddingResponse:
    """Normalized embedding response from an LLM provider."""

    embedding: list[float] = field(default_factory=list)
    model: str = ""
    elapsed_time: float = 0.0


@dataclass(frozen=True)
class ModelInfo:
    """Normalized model metadata."""

    name: str
    size: int | None = None
    modified_at: str | None = None
