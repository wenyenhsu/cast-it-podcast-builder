"""LLM application settings."""

from dataclasses import dataclass

from django.conf import settings

from domain.llm.config import LLMProviderConfig


@dataclass(frozen=True)
class LLMSettings:
    """Application-level LLM configuration loaded from environment variables."""

    provider: str
    base_url: str
    chat_model: str
    embedding_model: str
    temperature: float
    timeout: float
    retry_count: int
    max_prompt_chars: int

    @classmethod
    def from_django_settings(cls) -> "LLMSettings":
        """Load settings from Django configuration."""
        return cls(
            provider=getattr(settings, "LLM_PROVIDER", "ollama"),
            base_url=getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434"),
            chat_model=getattr(settings, "OLLAMA_CHAT_MODEL", ""),
            embedding_model=getattr(settings, "OLLAMA_EMBED_MODEL", ""),
            temperature=float(getattr(settings, "LLM_TEMPERATURE", 0.7)),
            timeout=float(getattr(settings, "LLM_TIMEOUT", 60.0)),
            retry_count=int(getattr(settings, "LLM_RETRY_COUNT", 3)),
            max_prompt_chars=int(getattr(settings, "LLM_MAX_PROMPT_CHARS", 100_000)),
        )

    def to_provider_config(self) -> LLMProviderConfig:
        """Convert to provider-agnostic configuration."""
        return LLMProviderConfig(
            base_url=self.base_url,
            chat_model=self.chat_model,
            embedding_model=self.embedding_model,
            temperature=self.temperature,
            timeout=self.timeout,
        )
