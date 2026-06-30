"""Aggregated health check service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domain.observability.dtos import HealthCheckResult, HealthSummary
from domain.observability.enums import HealthStatus
from services.observability.health.infrastructure import InfrastructureHealthService
from services.observability.health.provider import ProviderHealthService


class HealthCheckService:
    """Aggregate infrastructure and provider health into a unified report."""

    def __init__(
        self,
        infrastructure: InfrastructureHealthService | None = None,
        providers: ProviderHealthService | None = None,
    ) -> None:
        self._infrastructure = infrastructure or InfrastructureHealthService()
        self._providers = providers or ProviderHealthService()

    def check_all(self) -> HealthSummary:
        components = self._infrastructure.check_all() + self._providers.check_all()
        return self._summarize(components)

    def check_components(self) -> list[dict[str, Any]]:
        summary = self.check_all()
        return [self._component_dict(item) for item in summary.components]

    def overall_status(self) -> dict[str, Any]:
        summary = self.check_all()
        return {
            "status": summary.status.value,
            "checked_at": summary.checked_at.isoformat(),
            "healthy_count": summary.healthy_count,
            "warning_count": summary.warning_count,
            "unhealthy_count": summary.unhealthy_count,
            "unknown_count": summary.unknown_count,
            "components": self.check_components(),
        }

    def _summarize(self, components: list[HealthCheckResult]) -> HealthSummary:
        healthy = sum(1 for c in components if c.status == HealthStatus.HEALTHY)
        warning = sum(1 for c in components if c.status == HealthStatus.WARNING)
        unhealthy = sum(1 for c in components if c.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for c in components if c.status == HealthStatus.UNKNOWN)

        if unhealthy > 0:
            overall = HealthStatus.UNHEALTHY
        elif warning > 0:
            overall = HealthStatus.WARNING
        elif healthy == 0 and unknown > 0:
            overall = HealthStatus.UNKNOWN
        else:
            overall = HealthStatus.HEALTHY

        return HealthSummary(
            status=overall,
            checked_at=datetime.now(tz=UTC),
            components=components,
            healthy_count=healthy,
            warning_count=warning,
            unhealthy_count=unhealthy,
            unknown_count=unknown,
        )

    @staticmethod
    def _component_dict(result: HealthCheckResult) -> dict[str, Any]:
        return {
            "component": result.component,
            "status": result.status.value,
            "checked_at": result.checked_at.isoformat(),
            "latency_ms": result.latency_ms,
            "error_message": result.error_message,
            "metadata": result.metadata,
        }
