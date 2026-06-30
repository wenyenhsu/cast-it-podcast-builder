"""Provider status aggregation for the operations provider dashboards."""

import time
from typing import Any

from django.utils import timezone

from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings
from services.llm.provider_factory import LLMProviderFactory
from services.llm.settings import LLMSettings


class ProviderDashboardService:
    """Collects LLM and TTS provider health for the operations dashboards."""

    def snapshot(self) -> list[dict[str, Any]]:
        return [self.llm_status(), self.tts_status()]

    def llm_status(self) -> dict[str, Any]:
        settings = LLMSettings.from_django_settings()
        started = time.perf_counter()
        healthy = False
        available_models: list[str] = []
        try:
            provider = LLMProviderFactory(settings).create()
            healthy = provider.health_check()
            if hasattr(provider, "list_models"):
                models = provider.list_models()
                available_models = [
                    getattr(model, "name", str(model)) for model in models
                ]
        except Exception:
            healthy = False
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            **self._row(
                name="LLM",
                backend=settings.provider,
                provider_type="llm",
                healthy=healthy,
                response_time_ms=elapsed_ms,
                active_model=settings.chat_model,
                available_models=available_models,
            ),
            "base_url": settings.base_url,
            "chat_model": settings.chat_model,
            "embedding_model": settings.embedding_model,
            "temperature": settings.temperature,
            "timeout": settings.timeout,
        }

    def tts_status(self) -> dict[str, Any]:
        settings = TTSSettings.from_django_settings()
        started = time.perf_counter()
        healthy = False
        try:
            provider = TTSProviderFactory(settings).create()
            healthy = provider.health_check()
        except Exception:
            healthy = False
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return {
            **self._row(
                name="TTS",
                backend=settings.provider,
                provider_type="tts",
                healthy=healthy,
                response_time_ms=elapsed_ms,
                active_model=settings.default_voice,
                available_models=[],
            ),
            "base_url": settings.base_url,
            "default_voice": settings.default_voice,
            "audio_format": settings.audio_format,
            "timeout": settings.timeout,
            "max_text_length": settings.max_text_length,
            "words_per_minute": settings.words_per_minute,
        }

    def _row(
        self,
        *,
        name: str,
        backend: str,
        provider_type: str,
        healthy: bool,
        response_time_ms: int | None,
        active_model: str,
        available_models: list[str],
        last_check=None,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "backend": backend,
            "provider_type": provider_type,
            "health": "Healthy" if healthy else "Error",
            "healthy": healthy,
            "response_time_ms": response_time_ms,
            "last_check": last_check or timezone.now(),
            "active_model": active_model,
            "available_models": available_models,
        }
