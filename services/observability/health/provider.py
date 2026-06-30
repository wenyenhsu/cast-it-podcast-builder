"""External provider health checks."""

from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import Any

from domain.observability.dtos import HealthCheckResult
from domain.observability.enums import HealthStatus
from infrastructure.publish.providers.factory import PublisherFactory
from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings
from services.knowledge.health import KnowledgeHealthService
from services.llm.provider_factory import LLMProviderFactory
from services.llm.settings import LLMSettings
from services.publish.settings import PublishSettings


class ProviderHealthService:
    """Health probes for external providers and adapters."""

    def check_all(self) -> list[HealthCheckResult]:
        return [
            self.check_ollama(),
            self.check_chatterbox(),
            self.check_vector_store(),
            self.check_embedding_provider(),
            self.check_youtube(),
            self.check_rss_feed(),
        ]

    def check_ollama(self) -> HealthCheckResult:
        start = time.perf_counter()
        settings = LLMSettings.from_django_settings()
        provider = LLMProviderFactory(settings).create()
        healthy = provider.health_check()
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            component="ollama",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            error_message="" if healthy else "LLM provider health check failed",
            metadata={"provider": settings.provider},
        )

    def check_chatterbox(self) -> HealthCheckResult:
        start = time.perf_counter()
        settings = TTSSettings.from_django_settings()
        provider = TTSProviderFactory(settings).create()
        healthy = provider.health_check()
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            component="chatterbox",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            error_message="" if healthy else "TTS provider health check failed",
            metadata={"provider": settings.provider},
        )

    def check_vector_store(self) -> HealthCheckResult:
        start = time.perf_counter()
        knowledge = KnowledgeHealthService().check_all()
        latency_ms = (time.perf_counter() - start) * 1000
        healthy = bool(knowledge.get("healthy"))
        return HealthCheckResult(
            component="vector_store",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            metadata=knowledge,
        )

    def check_embedding_provider(self) -> HealthCheckResult:
        start = time.perf_counter()
        knowledge = KnowledgeHealthService().check_all()
        latency_ms = (time.perf_counter() - start) * 1000
        embedding_ok = bool(knowledge.get("embedding", {}).get("healthy", False))
        return HealthCheckResult(
            component="embedding_provider",
            status=HealthStatus.HEALTHY if embedding_ok else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            metadata={"embedding": knowledge.get("embedding", {})},
        )

    def check_youtube(self) -> HealthCheckResult:
        start = time.perf_counter()
        settings = PublishSettings.from_django_settings()
        publishers = PublisherFactory(settings).enabled_publishers()
        youtube = publishers.get("youtube")
        latency_ms = (time.perf_counter() - start) * 1000
        if youtube is None:
            return HealthCheckResult(
                component="youtube_publishing",
                status=HealthStatus.UNKNOWN,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                metadata={"enabled": False},
            )
        healthy = youtube.health_check()
        return HealthCheckResult(
            component="youtube_publishing",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            metadata={"enabled": True},
        )

    def check_rss_feed(self) -> HealthCheckResult:
        start = time.perf_counter()
        settings = PublishSettings.from_django_settings()
        publishers = PublisherFactory(settings).enabled_publishers()
        rss = publishers.get("rss")
        latency_ms = (time.perf_counter() - start) * 1000
        if rss is None:
            return HealthCheckResult(
                component="rss_feed_generator",
                status=HealthStatus.UNKNOWN,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                metadata={"enabled": False},
            )
        healthy = rss.health_check()
        return HealthCheckResult(
            component="rss_feed_generator",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            metadata={"enabled": True},
        )

    @staticmethod
    def result_to_dict(result: HealthCheckResult) -> dict[str, Any]:
        return {
            "component": result.component,
            "status": result.status.value,
            "checked_at": result.checked_at.isoformat(),
            "latency_ms": result.latency_ms,
            "error_message": result.error_message,
            "metadata": result.metadata,
        }
