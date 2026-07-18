"""Tests for Ollama LLM provider."""

from unittest.mock import MagicMock

import pytest

from domain.llm.config import LLMProviderConfig
from domain.llm.dtos import LLMRequest
from domain.llm.exceptions import (
    InvalidResponseException,
    ProviderUnavailableException,
    TimeoutException,
)
from infrastructure.llm.providers.ollama import OllamaProvider


@pytest.fixture
def provider_config() -> LLMProviderConfig:
    return LLMProviderConfig(
        base_url="http://ollama.test",
        chat_model="test-chat-model",
        embedding_model="test-embed-model",
        temperature=0.7,
        timeout=5.0,
    )


class MockHTTPResponse:
    """Minimal HTTP response double for provider tests."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def json(self) -> dict[str, object]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


class TestOllamaProvider:
    def test_chat_returns_normalized_response(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.post.return_value = MockHTTPResponse(
            {
                "model": "test-chat-model",
                "message": {"role": "assistant", "content": "Hello there"},
                "done": True,
                "prompt_eval_count": 12,
                "eval_count": 8,
            }
        )
        provider = OllamaProvider(provider_config, http_client=http_client)

        response = provider.chat(
            LLMRequest(system_prompt="You are helpful.", user_prompt="Hi")
        )

        assert response.content == "Hello there"
        assert response.model == "test-chat-model"
        assert response.prompt_tokens == 12
        assert response.completion_tokens == 8
        assert response.total_tokens == 20
        assert response.finish_reason == "stop"

    def test_generate_returns_normalized_response(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.post.return_value = MockHTTPResponse(
            {
                "model": "test-chat-model",
                "response": "Generated text",
                "done": True,
                "prompt_eval_count": 5,
                "eval_count": 3,
            }
        )
        provider = OllamaProvider(provider_config, http_client=http_client)

        response = provider.generate(LLMRequest(user_prompt="Write something"))

        assert response.content == "Generated text"
        assert response.completion_tokens == 3

    def test_chat_sends_json_schema_to_ollama(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.post.return_value = MockHTTPResponse(
            {
                "model": "test-chat-model",
                "message": {"role": "assistant", "content": '{"ok": true}'},
                "done": True,
            }
        )
        provider = OllamaProvider(provider_config, http_client=http_client)
        schema = {"type": "object", "properties": {"ok": {"type": "boolean"}}}

        provider.chat(
            LLMRequest(user_prompt="Return JSON", json_mode=True, json_schema=schema)
        )

        assert http_client.post.call_args.kwargs["json"]["format"] == schema

    def test_list_models_returns_normalized_metadata(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.get.return_value = MockHTTPResponse(
            {
                "models": [
                    {"name": "test-chat-model", "size": 100, "modified_at": "today"},
                    {"name": "test-embed-model", "size": 50},
                ]
            }
        )
        provider = OllamaProvider(provider_config, http_client=http_client)

        models = provider.list_models()

        assert len(models) == 2
        assert models[0].name == "test-chat-model"
        assert models[0].size == 100

    def test_embed_returns_normalized_vector(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.post.return_value = MockHTTPResponse(
            {"embeddings": [[0.1, 0.2, 0.3]]}
        )
        provider = OllamaProvider(provider_config, http_client=http_client)

        response = provider.embed("hello world")

        assert response.embedding == [0.1, 0.2, 0.3]
        assert response.model == "test-embed-model"

    def test_health_check_passes_when_models_exist(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.get.return_value = MockHTTPResponse(
            {
                "models": [
                    {"name": "test-chat-model"},
                    {"name": "test-embed-model"},
                ]
            }
        )
        provider = OllamaProvider(provider_config, http_client=http_client)

        assert provider.health_check() is True

    def test_health_check_fails_when_model_missing(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.get.return_value = MockHTTPResponse(
            {"models": [{"name": "other-model"}]}
        )
        provider = OllamaProvider(provider_config, http_client=http_client)

        assert provider.health_check() is False

    def test_post_timeout_raises_timeout_exception(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.post.side_effect = TimeoutError("timed out")
        provider = OllamaProvider(provider_config, http_client=http_client)

        with pytest.raises(TimeoutException):
            provider.chat(LLMRequest(user_prompt="Hi"))

    def test_post_failure_raises_provider_unavailable(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        http_client.post.side_effect = ConnectionError("connection refused")
        provider = OllamaProvider(provider_config, http_client=http_client)

        with pytest.raises(ProviderUnavailableException):
            provider.chat(LLMRequest(user_prompt="Hi"))

    def test_invalid_json_raises_invalid_response(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        bad_response = MagicMock()
        bad_response.json.side_effect = ValueError("invalid json")
        bad_response.raise_for_status.return_value = None
        http_client.post.return_value = bad_response
        provider = OllamaProvider(provider_config, http_client=http_client)

        with pytest.raises(InvalidResponseException):
            provider.chat(LLMRequest(user_prompt="Hi"))

    def test_stream_yields_content_chunks(
        self,
        provider_config: LLMProviderConfig,
    ) -> None:
        http_client = MagicMock()
        stream_context = MagicMock()
        stream_response = MagicMock()
        stream_response.iter_lines.return_value = [
            b'{"message": {"content": "Hel"}, "done": false}',
            b'{"message": {"content": "lo"}, "done": true}',
        ]
        stream_context.__enter__.return_value = stream_response
        stream_context.__exit__.return_value = None
        http_client.stream.return_value = stream_context

        provider = OllamaProvider(provider_config, http_client=http_client)
        chunks = list(provider.stream(LLMRequest(user_prompt="Hi")))

        assert chunks == ["Hel", "lo"]
