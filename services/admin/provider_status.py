"""Provider status aggregation for the admin provider dashboard."""

import time
from typing import Any

from django.utils import timezone

from apps.providers.models import ProviderHealthCheck
from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings
from services.llm.provider_factory import LLMProviderFactory
from services.llm.settings import LLMSettings
from services.publish.settings import PublishSettings


class ProviderDashboardService:
    """Collects provider health and metadata for the admin dashboard."""

    PROVIDERS = ("Ollama", "Chatterbox", "RSS", "Gmail", "YouTube")

    def snapshot(self) -> list[dict[str, Any]]:
        return [
            self._ollama_status(),
            self._chatterbox_status(),
            self._rss_status(),
            self._gmail_status(),
            self._youtube_status(),
        ]

    def run_health_checks(self) -> list[dict[str, Any]]:
        return self.snapshot()

    def _ollama_status(self) -> dict[str, Any]:
        settings = LLMSettings.from_django_settings()
        started = time.perf_counter()
        healthy = False
        active_model = settings.chat_model or ""
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
        return self._row(
            name="Ollama",
            provider_type="llm",
            healthy=healthy,
            response_time_ms=elapsed_ms,
            version="",
            active_model=active_model,
            available_models=available_models,
        )

    def _chatterbox_status(self) -> dict[str, Any]:
        settings = TTSSettings.from_django_settings()
        started = time.perf_counter()
        healthy = False
        try:
            provider = TTSProviderFactory(settings).create()
            healthy = provider.health_check()
        except Exception:
            healthy = False
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        return self._row(
            name="Chatterbox",
            provider_type="tts",
            healthy=healthy,
            response_time_ms=elapsed_ms,
            version="",
            active_model=settings.default_voice,
            available_models=[],
        )

    def _rss_status(self) -> dict[str, Any]:
        last = (
            ProviderHealthCheck.objects.filter(provider_type="rss")
            .order_by("-checked_at")
            .first()
        )
        return self._row(
            name="RSS",
            provider_type="rss",
            healthy=last.status == "healthy" if last else True,
            response_time_ms=last.response_time_ms if last else None,
            version="",
            active_model="",
            available_models=[],
            last_check=last.checked_at if last else None,
        )

    def _gmail_status(self) -> dict[str, Any]:
        return self._row(
            name="Gmail",
            provider_type="gmail",
            healthy=False,
            response_time_ms=None,
            version="",
            active_model="",
            available_models=[],
            note="Not configured",
        )

    def _youtube_status(self) -> dict[str, Any]:
        settings = PublishSettings.from_django_settings()
        healthy = settings.youtube_configured()
        return self._row(
            name="YouTube",
            provider_type="youtube",
            healthy=healthy,
            response_time_ms=None,
            version="",
            active_model=settings.youtube_channel_id,
            available_models=[],
            note="Configured" if healthy else "Not configured",
        )

    def _row(
        self,
        *,
        name: str,
        provider_type: str,
        healthy: bool,
        response_time_ms: int | None,
        version: str,
        active_model: str,
        available_models: list[str],
        last_check=None,
        note: str = "",
    ) -> dict[str, Any]:
        if healthy:
            health = "Healthy"
        elif note == "Not configured":
            health = "Warning"
        else:
            health = "Error"
        return {
            "name": name,
            "provider_type": provider_type,
            "health": health,
            "healthy": healthy,
            "response_time_ms": response_time_ms,
            "last_check": last_check or timezone.now(),
            "version": version,
            "active_model": active_model,
            "available_models": available_models,
            "note": note,
        }
