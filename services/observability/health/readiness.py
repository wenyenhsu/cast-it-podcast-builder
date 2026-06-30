"""System readiness and liveness checks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domain.observability.enums import HealthStatus
from services.observability.health.check_service import HealthCheckService


class SystemReadinessService:
    """Determine whether the system is ready to process jobs."""

    def __init__(self, health: HealthCheckService | None = None) -> None:
        self._health = health or HealthCheckService()

    def liveness(self) -> dict[str, Any]:
        """Return liveness probe result (process is running)."""
        return {
            "status": HealthStatus.HEALTHY.value,
            "checked_at": datetime.now(tz=UTC).isoformat(),
            "message": "Application process is alive",
        }

    def readiness(self) -> dict[str, Any]:
        """Return readiness probe based on critical dependencies."""
        summary = self._health.check_all()
        critical = {"postgresql", "redis", "celery_workers"}
        critical_results = [
            component
            for component in summary.components
            if component.component in critical
        ]
        ready = all(
            component.status in {HealthStatus.HEALTHY, HealthStatus.WARNING}
            for component in critical_results
        )
        status_value = (
            HealthStatus.HEALTHY.value if ready else HealthStatus.UNHEALTHY.value
        )
        return {
            "status": status_value,
            "ready": ready,
            "checked_at": datetime.now(tz=UTC).isoformat(),
            "critical_components": [
                {
                    "component": item.component,
                    "status": item.status.value,
                    "latency_ms": item.latency_ms,
                    "error_message": item.error_message,
                }
                for item in critical_results
            ],
        }
