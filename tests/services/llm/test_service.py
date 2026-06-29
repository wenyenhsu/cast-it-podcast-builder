"""Tests for LLM service."""

from unittest.mock import MagicMock

import pytest

from domain.llm.dtos import EmbeddingResponse, LLMRequest, LLMResponse, ModelInfo
from domain.llm.exceptions import (
    LLMException,
    PromptTooLargeException,
    ProviderUnavailableException,
    TimeoutException,
)
from services.llm.service import LLMService
from services.llm.settings import LLMSettings


@pytest.fixture
def llm_settings() -> LLMSettings:
    return LLMSettings(
        provider="ollama",
        base_url="http://ollama.test",
        chat_model="test-chat-model",
        embedding_model="test-embed-model",
        temperature=0.7,
        timeout=5.0,
        retry_count=3,
        max_prompt_chars=100,
    )


@pytest.fixture
def mock_provider() -> MagicMock:
    provider = MagicMock()
    provider.chat.return_value = LLMResponse(
        content="Response",
        model="test-chat-model",
        prompt_tokens=5,
        completion_tokens=3,
        total_tokens=8,
        finish_reason="stop",
        elapsed_time=0.2,
    )
    provider.generate.return_value = provider.chat.return_value
    provider.embed.return_value = EmbeddingResponse(
        embedding=[0.1, 0.2],
        model="test-embed-model",
        elapsed_time=0.1,
    )
    provider.list_models.return_value = [ModelInfo(name="test-chat-model")]
    provider.health_check.return_value = True
    return provider


class TestLLMService:
    def test_chat_delegates_to_provider(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)
        request = LLMRequest(user_prompt="Hello")

        response = service.chat(request)

        assert response.content == "Response"
        mock_provider.chat.assert_called_once_with(request)

    def test_generate_delegates_to_provider(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)
        request = LLMRequest(user_prompt="Hello")

        service.generate(request)

        mock_provider.generate.assert_called_once_with(request)

    def test_embed_delegates_to_provider(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)

        response = service.embed("hello")

        assert response.embedding == [0.1, 0.2]
        mock_provider.embed.assert_called_once_with("hello")

    def test_empty_prompt_raises_error(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)

        with pytest.raises(LLMException):
            service.chat(LLMRequest())

    def test_oversized_prompt_raises_prompt_too_large(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)

        with pytest.raises(PromptTooLargeException):
            service.chat(LLMRequest(user_prompt="x" * 101))

    def test_retry_on_provider_unavailable(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        mock_provider.chat.side_effect = [
            ProviderUnavailableException("down"),
            ProviderUnavailableException("down"),
            LLMResponse(content="OK", model="test-chat-model"),
        ]
        service = LLMService(settings=llm_settings, provider=mock_provider)

        response = service.chat(LLMRequest(user_prompt="Hello"))

        assert response.content == "OK"
        assert mock_provider.chat.call_count == 3

    def test_retry_exhausted_raises_last_error(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        mock_provider.chat.side_effect = ProviderUnavailableException("down")
        service = LLMService(settings=llm_settings, provider=mock_provider)

        with pytest.raises(ProviderUnavailableException):
            service.chat(LLMRequest(user_prompt="Hello"))

        assert mock_provider.chat.call_count == 3

    def test_retry_on_timeout(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        mock_provider.generate.side_effect = [
            TimeoutException("slow"),
            LLMResponse(content="OK", model="test-chat-model"),
        ]
        service = LLMService(settings=llm_settings, provider=mock_provider)

        response = service.generate(LLMRequest(user_prompt="Hello"))

        assert response.content == "OK"
        assert mock_provider.generate.call_count == 2

    def test_health_check_delegates_to_provider(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)
        assert service.health_check() is True

    def test_list_models_delegates_to_provider(
        self,
        llm_settings: LLMSettings,
        mock_provider: MagicMock,
    ) -> None:
        service = LLMService(settings=llm_settings, provider=mock_provider)
        models = service.list_models()
        assert models[0].name == "test-chat-model"
