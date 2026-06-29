"""LLM orchestration service."""

import logging
import time
from collections.abc import Callable, Iterator
from typing import TypeVar

from domain.llm.dtos import EmbeddingResponse, LLMRequest, LLMResponse, ModelInfo
from domain.llm.exceptions import (
    LLMException,
    PromptTooLargeException,
    ProviderUnavailableException,
    TimeoutException,
)
from infrastructure.llm.providers.base import BaseLLMProvider
from services.llm.provider_factory import LLMProviderFactory
from services.llm.settings import LLMSettings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class LLMService:
    """High-level service for interacting with LLM providers."""

    def __init__(
        self,
        settings: LLMSettings | None = None,
        provider: BaseLLMProvider | None = None,
    ) -> None:
        self._settings = settings or LLMSettings.from_django_settings()
        self._provider = provider or LLMProviderFactory(self._settings).create()

    def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a completion using the configured provider."""
        self._validate_request(request)
        return self._execute_with_retry(
            operation="generate",
            func=self._provider.generate,
            request=request,
        )

    def chat(self, request: LLMRequest) -> LLMResponse:
        """Generate a chat-style completion using the configured provider."""
        self._validate_request(request)
        return self._execute_with_retry(
            operation="chat",
            func=self._provider.chat,
            request=request,
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        """Stream a chat completion from the configured provider."""
        self._validate_request(request)
        started = time.perf_counter()
        logger.info(
            "LLM stream started",
            extra={
                "event": "llm_stream_started",
                "provider": self._settings.provider,
                "model": self._settings.chat_model,
            },
        )

        try:
            yield from self._provider.stream(request)
        except (ProviderUnavailableException, TimeoutException, LLMException):
            logger.exception(
                "LLM stream failed",
                extra={
                    "event": "llm_stream_error",
                    "provider": self._settings.provider,
                    "model": self._settings.chat_model,
                },
            )
            raise
        finally:
            elapsed = time.perf_counter() - started
            logger.info(
                "LLM stream finished",
                extra={
                    "event": "llm_stream_finished",
                    "provider": self._settings.provider,
                    "model": self._settings.chat_model,
                    "elapsed_time": elapsed,
                },
            )

    def embed(self, text: str) -> EmbeddingResponse:
        """Generate an embedding vector for the given text."""
        if not text.strip():
            raise LLMException("Embedding input must not be empty.")

        return self._execute_with_retry(
            operation="embed",
            func=lambda _request: self._provider.embed(text),
            request=LLMRequest(user_prompt=text),
        )

    def list_models(self) -> list[ModelInfo]:
        """Return normalized model metadata from the provider."""
        return self._provider.list_models()

    def health_check(self) -> bool:
        """Verify the configured provider is healthy."""
        return self._provider.health_check()

    def _validate_request(self, request: LLMRequest) -> None:
        if not request.user_prompt.strip() and not request.system_prompt.strip():
            raise LLMException("At least one prompt field must be provided.")

        total_chars = len(request.system_prompt) + len(request.user_prompt)
        if total_chars > self._settings.max_prompt_chars:
            raise PromptTooLargeException(
                f"Prompt exceeds maximum size of {self._settings.max_prompt_chars} "
                f"characters ({total_chars} provided)."
            )

    def _execute_with_retry(
        self,
        *,
        operation: str,
        func: Callable[[LLMRequest], T],
        request: LLMRequest,
    ) -> T:
        last_error: Exception | None = None
        retries = self._settings.retry_count

        for attempt in range(1, retries + 1):
            started = time.perf_counter()
            try:
                result = func(request)
                elapsed = time.perf_counter() - started
                self._log_success(operation, result, elapsed, attempt)
                return result
            except (ProviderUnavailableException, TimeoutException) as exc:
                last_error = exc
                logger.warning(
                    "LLM request failed, retrying",
                    extra={
                        "event": "llm_retry",
                        "operation": operation,
                        "provider": self._settings.provider,
                        "model": self._settings.chat_model,
                        "attempt": attempt,
                        "retry_count": retries,
                        "error": str(exc),
                    },
                )

        assert last_error is not None
        logger.error(
            "LLM request failed after retries",
            extra={
                "event": "llm_error",
                "operation": operation,
                "provider": self._settings.provider,
                "model": self._settings.chat_model,
                "retry_count": retries,
                "error": str(last_error),
            },
        )
        raise last_error

    def _log_success(
        self,
        operation: str,
        result: T,
        elapsed: float,
        attempt: int,
    ) -> None:
        extra: dict[str, object] = {
            "event": "llm_success",
            "operation": operation,
            "provider": self._settings.provider,
            "model": self._settings.chat_model,
            "elapsed_time": elapsed,
            "retry_count": attempt,
        }

        if isinstance(result, LLMResponse):
            extra.update(
                {
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "total_tokens": result.total_tokens,
                    "finish_reason": result.finish_reason,
                }
            )
        elif isinstance(result, EmbeddingResponse):
            extra.update({"embedding_dimensions": len(result.embedding)})

        logger.info("LLM request completed", extra=extra)
