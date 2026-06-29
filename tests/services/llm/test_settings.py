"""Tests for LLM settings."""

from django.test import override_settings

from services.llm.settings import LLMSettings


class TestLLMSettings:
    @override_settings(
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://custom:11434",
        OLLAMA_CHAT_MODEL="custom-chat",
        OLLAMA_EMBED_MODEL="custom-embed",
        LLM_TEMPERATURE=0.5,
        LLM_TIMEOUT=30.0,
        LLM_RETRY_COUNT=2,
        LLM_MAX_PROMPT_CHARS=5000,
    )
    def test_from_django_settings(self) -> None:
        settings = LLMSettings.from_django_settings()

        assert settings.provider == "ollama"
        assert settings.base_url == "http://custom:11434"
        assert settings.chat_model == "custom-chat"
        assert settings.embedding_model == "custom-embed"
        assert settings.temperature == 0.5
        assert settings.timeout == 30.0
        assert settings.retry_count == 2
        assert settings.max_prompt_chars == 5000

    def test_to_provider_config(self) -> None:
        settings = LLMSettings(
            provider="ollama",
            base_url="http://localhost:11434",
            chat_model="chat",
            embedding_model="embed",
            temperature=0.7,
            timeout=60.0,
            retry_count=3,
            max_prompt_chars=100_000,
        )
        config = settings.to_provider_config()

        assert config.chat_model == "chat"
        assert config.embedding_model == "embed"
        assert config.base_url == "http://localhost:11434"
