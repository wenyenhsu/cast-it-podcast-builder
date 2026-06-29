"""Tests for LLM DTOs."""

from domain.llm.dtos import EmbeddingResponse, LLMRequest, LLMResponse, ModelInfo


class TestLLMRequest:
    def test_defaults(self) -> None:
        request = LLMRequest(user_prompt="Hello")
        assert request.system_prompt == ""
        assert request.user_prompt == "Hello"
        assert request.json_mode is False
        assert request.temperature is None


class TestLLMResponse:
    def test_token_fields(self) -> None:
        response = LLMResponse(
            content="Hi",
            model="test-model",
            prompt_tokens=10,
            completion_tokens=5,
            total_tokens=15,
            finish_reason="stop",
            elapsed_time=0.5,
        )
        assert response.total_tokens == 15
        assert response.finish_reason == "stop"


class TestEmbeddingResponse:
    def test_embedding_vector(self) -> None:
        response = EmbeddingResponse(
            embedding=[0.1, 0.2, 0.3],
            model="embed-model",
            elapsed_time=0.1,
        )
        assert len(response.embedding) == 3


class TestModelInfo:
    def test_model_metadata(self) -> None:
        model = ModelInfo(name="llama3.2", size=1024, modified_at="2024-01-01")
        assert model.name == "llama3.2"
