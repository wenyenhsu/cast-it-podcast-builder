"""Infrastructure component health checks."""

from __future__ import annotations

import shutil
import time
from datetime import UTC, datetime
from typing import Any

from django.conf import settings as django_settings
from django.core.cache import cache

from domain.observability.dtos import HealthCheckResult
from domain.observability.enums import HealthStatus
from infrastructure.celery.health import CeleryHealthService
from services.audio.pipeline.settings import AudioSettings


class InfrastructureHealthService:
    """Health probes for core infrastructure components."""

    def check_all(self) -> list[HealthCheckResult]:
        checks = [
            self.check_postgresql,
            self.check_redis,
            self.check_celery,
            self.check_celery_beat,
            self.check_ffmpeg,
            self.check_storage,
        ]
        return [probe() for probe in checks]

    def check_postgresql(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            from django.db import connection

            connection.ensure_connection()
            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(
                component="postgresql",
                status=HealthStatus.HEALTHY,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                metadata={"engine": django_settings.DATABASES["default"]["ENGINE"]},
            )
        except Exception as exc:
            return self._error("postgresql", start, str(exc))

    def check_redis(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            cache.set("observability_health_ping", "ok", timeout=5)
            healthy = cache.get("observability_health_ping") == "ok"
            latency_ms = (time.perf_counter() - start) * 1000
            status = HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY
            return HealthCheckResult(
                component="redis",
                status=status,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                error_message="" if healthy else "Cache ping failed",
            )
        except Exception as exc:
            return self._error("redis", start, str(exc))

    def check_celery(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            result = CeleryHealthService().check_all()
            latency_ms = (time.perf_counter() - start) * 1000
            healthy = bool(result.get("healthy"))
            status = HealthStatus.HEALTHY if healthy else HealthStatus.WARNING
            return HealthCheckResult(
                component="celery_workers",
                status=status,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                metadata={
                    "workers": result.get("workers"),
                    "redis": result.get("redis"),
                },
            )
        except Exception as exc:
            return self._error("celery_workers", start, str(exc))

    def check_celery_beat(self) -> HealthCheckResult:
        start = time.perf_counter()
        try:
            from django_celery_beat.models import PeriodicTask

            count = PeriodicTask.objects.filter(enabled=True).count()
            latency_ms = (time.perf_counter() - start) * 1000
            status = HealthStatus.HEALTHY if count > 0 else HealthStatus.WARNING
            return HealthCheckResult(
                component="celery_beat",
                status=status,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                metadata={"enabled_tasks": count},
            )
        except Exception as exc:
            return self._error("celery_beat", start, str(exc))

    def check_ffmpeg(self) -> HealthCheckResult:
        start = time.perf_counter()
        audio_settings = AudioSettings.from_django_settings()
        ffmpeg = shutil.which(audio_settings.ffmpeg_binary)
        ffprobe = shutil.which(audio_settings.ffprobe_binary)
        latency_ms = (time.perf_counter() - start) * 1000
        healthy = bool(ffmpeg and ffprobe)
        return HealthCheckResult(
            component="ffmpeg",
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            error_message="" if healthy else "FFmpeg binaries not found",
            metadata={"ffmpeg": ffmpeg or "", "ffprobe": ffprobe or ""},
        )

    def check_storage(self) -> HealthCheckResult:
        start = time.perf_counter()
        media_root = django_settings.MEDIA_ROOT
        try:
            media_root.mkdir(parents=True, exist_ok=True)
            test_file = media_root / ".observability_health_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            latency_ms = (time.perf_counter() - start) * 1000
            return HealthCheckResult(
                component="storage",
                status=HealthStatus.HEALTHY,
                checked_at=datetime.now(tz=UTC),
                latency_ms=round(latency_ms, 2),
                metadata={"path": str(media_root)},
            )
        except Exception as exc:
            return self._error("storage", start, str(exc))

    @staticmethod
    def _error(component: str, start: float, message: str) -> HealthCheckResult:
        latency_ms = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            checked_at=datetime.now(tz=UTC),
            latency_ms=round(latency_ms, 2),
            error_message=message,
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
