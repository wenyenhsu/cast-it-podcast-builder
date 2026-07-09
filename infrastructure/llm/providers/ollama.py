"""Ollama LLM provider adapter."""

import json
import logging
import os
import time
from collections.abc import Iterator
from typing import Any, Protocol

from domain.llm.config import LLMProviderConfig
from domain.llm.dtos import EmbeddingResponse, LLMRequest, LLMResponse, ModelInfo
from domain.llm.exceptions import (
    InvalidResponseException,
    ProviderUnavailableException,
    TimeoutException,
)
from infrastructure.llm.providers.base import BaseLLMProvider

logger = logging.getLogger(__name__)


class HTTPClientProtocol(Protocol):
    """Protocol for HTTP clients used by OllamaProvider."""

    def get(self, url: str, *, timeout: float) -> Any: ...

    def post(self, url: str, *, json: dict[str, Any], timeout: float) -> Any: ...


class HTTPStreamClientProtocol(HTTPClientProtocol, Protocol):
    """Extended protocol for clients that support streaming responses."""

    def stream(
        self,
        method: str,
        url: str,
        *,
        json: dict[str, Any],
        timeout: float,
    ) -> Any: ...


class OllamaProvider(BaseLLMProvider):
    """Adapter for the Ollama HTTP API."""

    def __init__(
        self,
        config: LLMProviderConfig,
        http_client: HTTPClientProtocol | None = None,
    ) -> None:
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        self._chat_model = config.chat_model
        self._embed_model = config.embedding_model
        self._default_temperature = config.temperature
        self._timeout = config.timeout

        if http_client is None:
            import httpx

            http_client = httpx.Client()
        self._http = http_client

    def generate(self, request: LLMRequest) -> LLMResponse:
        prompt = self._build_prompt(request)
        payload: dict[str, Any] = {
            "model": self._chat_model,
            "prompt": prompt,
            "stream": False,
            "options": self._build_options(request),
        }
        if request.json_mode:
            payload["format"] = "json"

        data = self._post("/api/generate", payload)
        return self._parse_completion_response(
            data,
            request_elapsed=float(data.get("_elapsed", 0.0)),
        )

    def chat(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._chat_model,
            "messages": self._build_messages(request),
            "stream": False,
            "options": self._build_options(request),
        }
        if request.json_mode:
            payload["format"] = "json"

        data = self._post("/api/chat", payload)
        return self._parse_chat_response(
            data,
            request_elapsed=float(data.get("_elapsed", 0.0)),
        )

    def stream(self, request: LLMRequest) -> Iterator[str]:
        if not hasattr(self._http, "stream"):
            raise ProviderUnavailableException(
                "Configured HTTP client does not support streaming."
            )

        payload: dict[str, Any] = {
            "model": self._chat_model,
            "messages": self._build_messages(request),
            "stream": True,
            "options": self._build_options(request),
        }
        if request.json_mode:
            payload["format"] = "json"

        url = f"{self._base_url}/api/chat"
        started = time.perf_counter()

        try:
            with self._http.stream(
                "POST",
                url,
                json=payload,
                timeout=self._timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    content = chunk.get("message", {}).get("content", "")
                    if content:
                        yield str(content)
                    if chunk.get("done"):
                        logger.info(
                            "Stream completed",
                            extra={
                                "event": "llm_stream_finished",
                                "provider": "ollama",
                                "model": self._chat_model,
                                "elapsed_time": time.perf_counter() - started,
                            },
                        )
                        break
        except TimeoutError as exc:
            raise TimeoutException("Ollama stream request timed out.") from exc
        except TimeoutException:
            raise
        except ProviderUnavailableException:
            raise
        except Exception as exc:
            if "timeout" in str(exc).lower():
                raise TimeoutException("Ollama stream request timed out.") from exc
            raise ProviderUnavailableException(
                f"Ollama stream request failed: {exc}"
            ) from exc

    def health_check(self) -> bool:
        try:
            self._get("/api/tags")
        except (ProviderUnavailableException, TimeoutException):
            return False

        models = self.list_models()
        model_names = {model.name for model in models}
        chat_available = self._chat_model in model_names
        embed_available = self._embed_model in model_names

        if not chat_available or not embed_available:
            logger.warning(
                "Configured Ollama models not found",
                extra={
                    "event": "llm_health_check_failed",
                    "provider": "ollama",
                    "chat_model": self._chat_model,
                    "embedding_model": self._embed_model,
                    "available_models": sorted(model_names),
                },
            )
            return False

        return True

    def list_models(self) -> list[ModelInfo]:
        data = self._get("/api/tags")
        models: list[ModelInfo] = []

        for entry in data.get("models", []):
            name = str(entry.get("name", "")).strip()
            if not name:
                continue
            models.append(
                ModelInfo(
                    name=name,
                    size=entry.get("size"),
                    modified_at=entry.get("modified_at"),
                )
            )

        return models

    def embed(self, text: str) -> EmbeddingResponse:
        payload = {
            "model": self._embed_model,
            "input": text,
        }
        started = time.perf_counter()
        data = self._post("/api/embed", payload)
        elapsed = time.perf_counter() - started

        embeddings = data.get("embeddings")
        if not embeddings or not isinstance(embeddings, list):
            raise InvalidResponseException("Ollama embed response missing embeddings.")

        vector = embeddings[0]
        if not isinstance(vector, list):
            raise InvalidResponseException("Ollama embed response has invalid format.")

        return EmbeddingResponse(
            embedding=[float(value) for value in vector],
            model=self._embed_model,
            elapsed_time=elapsed,
        )

    def _get(self, path: str) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        try:
            response = self._http.get(url, timeout=self._timeout)
            response.raise_for_status()
        except TimeoutError as exc:
            raise TimeoutException(f"Ollama GET {path} timed out.") from exc
        except TimeoutException:
            raise
        except Exception as exc:
            if "timeout" in str(exc).lower():
                raise TimeoutException(f"Ollama GET {path} timed out.") from exc
            raise ProviderUnavailableException(
                f"Ollama GET {path} failed: {exc}"
            ) from exc

        return self._parse_json(response)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        started = time.perf_counter()

        try:
            response = self._http.post(url, json=payload, timeout=self._timeout)
            response.raise_for_status()
        except TimeoutError as exc:
            raise TimeoutException(f"Ollama POST {path} timed out.") from exc
        except TimeoutException:
            raise
        except Exception as exc:
            if "timeout" in str(exc).lower():
                raise TimeoutException(f"Ollama POST {path} timed out.") from exc
            raise ProviderUnavailableException(
                f"Ollama POST {path} failed: {exc}"
            ) from exc

        data = self._parse_json(response)
        data["_elapsed"] = time.perf_counter() - started
        return data

    @staticmethod
    def _parse_json(response: Any) -> dict[str, Any]:
        try:
            parsed: dict[str, Any] = response.json()
        except Exception as exc:
            raise InvalidResponseException(
                "Ollama returned a non-JSON response."
            ) from exc
        return parsed

    def _build_options(self, request: LLMRequest) -> dict[str, Any]:
        options: dict[str, Any] = {
            "temperature": (
                request.temperature
                if request.temperature is not None
                else self._default_temperature
            ),
            # Ollama's default context window (often 4096) truncates long
            # prompts/outputs such as full podcast scripts.
            "num_ctx": int(os.environ.get("OLLAMA_NUM_CTX", "8192")),
        }
        if request.top_p is not None:
            options["top_p"] = request.top_p
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        return options

    @staticmethod
    def _build_messages(request: LLMRequest) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        if request.system_prompt.strip():
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.user_prompt})
        return messages

    @staticmethod
    def _build_prompt(request: LLMRequest) -> str:
        if request.system_prompt.strip():
            return f"{request.system_prompt.strip()}\n\n{request.user_prompt.strip()}"
        return request.user_prompt.strip()

    def _parse_completion_response(
        self,
        data: dict[str, Any],
        *,
        request_elapsed: float,
    ) -> LLMResponse:
        content = data.get("response")
        if content is None:
            raise InvalidResponseException("Ollama generate response missing content.")

        return LLMResponse(
            content=str(content),
            model=str(data.get("model", self._chat_model)),
            prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
            completion_tokens=int(data.get("eval_count", 0) or 0),
            total_tokens=int(
                (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
            ),
            finish_reason="stop" if data.get("done") else "unknown",
            elapsed_time=request_elapsed,
        )

    def _parse_chat_response(
        self,
        data: dict[str, Any],
        *,
        request_elapsed: float,
    ) -> LLMResponse:
        message = data.get("message", {})
        content = message.get("content")
        if content is None:
            raise InvalidResponseException("Ollama chat response missing content.")

        return LLMResponse(
            content=str(content),
            model=str(data.get("model", self._chat_model)),
            prompt_tokens=int(data.get("prompt_eval_count", 0) or 0),
            completion_tokens=int(data.get("eval_count", 0) or 0),
            total_tokens=int(
                (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
            ),
            finish_reason="stop" if data.get("done") else "unknown",
            elapsed_time=request_elapsed,
        )
