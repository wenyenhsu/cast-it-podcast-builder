"""Tests for LLM provider factory."""

from unittest.mock import MagicMock

import pytest

from domain.llm.exceptions import LLMException
from services.llm.provider_factory import LLMProviderFactory
from services.llm.settings import LLMSettings


class TestLLMProviderFactory:
    def test_creates_ollama_provider(self) -> None:
        settings = LLMSettings(
            provider="ollama",
            base_url="http://localhost:11434",
            chat_model="test-chat",
            embedding_model="test-embed",
            temperature=0.7,
            timeout=5.0,
            retry_count=3,
            max_prompt_chars=100_000,
        )
        factory = LLMProviderFactory(settings)
        provider = factory.create(http_client=MagicMock())

        assert provider.__class__.__name__ == "OllamaProvider"

    def test_unknown_provider_raises(self) -> None:
        settings = LLMSettings(
            provider="unknown",
            base_url="http://localhost",
            chat_model="x",
            embedding_model="y",
            temperature=0.7,
            timeout=5.0,
            retry_count=1,
            max_prompt_chars=1000,
        )
        factory = LLMProviderFactory(settings)

        with pytest.raises(LLMException):
            factory.create()
