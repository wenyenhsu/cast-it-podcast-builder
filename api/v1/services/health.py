"""Health check aggregation for API endpoints."""

from typing import Any

from infrastructure.celery.health import CeleryHealthService
from infrastructure.publish.providers.factory import PublisherFactory
from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings
from services.knowledge.health import KnowledgeHealthService
from services.llm.provider_factory import LLMProviderFactory
from services.llm.settings import LLMSettings
from services.publish.settings import PublishSettings


class ApiHealthService:
    """Aggregates subsystem health checks for the REST API."""

    def overall(self) -> dict[str, Any]:
        """Return overall platform health."""
        checks = {
            "celery": self.celery(),
            "llm": self.llm(),
            "tts": self.tts(),
            "publish": self.publish(),
            "knowledge": self.knowledge(),
        }
        healthy = all(
            check.get("healthy", False)
            for check in checks.values()
            if isinstance(check, dict)
        )
        return {"status": "ok" if healthy else "degraded", "checks": checks}

    def celery(self) -> dict[str, Any]:
        results = CeleryHealthService().check_all()
        return {"healthy": results.get("healthy", False), **results}

    def llm(self) -> dict[str, Any]:
        settings = LLMSettings.from_django_settings()
        provider = LLMProviderFactory(settings).create()
        healthy = provider.health_check()
        return {
            "healthy": healthy,
            "provider": settings.provider,
        }

    def tts(self) -> dict[str, Any]:
        settings = TTSSettings.from_django_settings()
        provider = TTSProviderFactory(settings).create()
        healthy = provider.health_check()
        return {
            "healthy": healthy,
            "provider": settings.provider,
        }

    def publish(self) -> dict[str, Any]:
        settings = PublishSettings.from_django_settings()
        publishers = PublisherFactory(settings).enabled_publishers()
        results = {
            platform: publisher.health_check()
            for platform, publisher in publishers.items()
        }
        healthy = all(results.values()) if results else True
        return {
            "healthy": healthy,
            "platforms": results,
            "enabled_platforms": list(settings.enabled_platforms()),
        }

    def knowledge(self) -> dict[str, Any]:
        return KnowledgeHealthService().check_all()
