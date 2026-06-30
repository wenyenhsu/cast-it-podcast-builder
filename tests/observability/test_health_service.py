"""Health check service tests."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest

from domain.observability.dtos import HealthCheckResult, HealthSummary
from domain.observability.enums import HealthStatus
from services.observability.health.check_service import HealthCheckService
from services.observability.health.readiness import SystemReadinessService


@pytest.mark.django_db
def test_liveness_always_healthy() -> None:
    result = SystemReadinessService().liveness()
    assert result["status"] == HealthStatus.HEALTHY.value


@pytest.mark.django_db
def test_readiness_with_mocked_health() -> None:
    now = datetime.now(tz=UTC)
    summary = HealthSummary(
        status=HealthStatus.HEALTHY,
        checked_at=now,
        components=[
            HealthCheckResult(
                component="postgresql",
                status=HealthStatus.HEALTHY,
                checked_at=now,
                latency_ms=1.0,
            ),
            HealthCheckResult(
                component="redis",
                status=HealthStatus.HEALTHY,
                checked_at=now,
                latency_ms=1.0,
            ),
            HealthCheckResult(
                component="celery_workers",
                status=HealthStatus.HEALTHY,
                checked_at=now,
                latency_ms=1.0,
            ),
        ],
        healthy_count=3,
        warning_count=0,
        unhealthy_count=0,
        unknown_count=0,
    )
    with patch.object(HealthCheckService, "check_all", return_value=summary):
        result = SystemReadinessService().readiness()
    assert result["ready"] is True


def test_health_summary_counts_statuses() -> None:
    now = datetime.now(tz=UTC)

    class FakeInfrastructure:
        def check_all(self) -> list[HealthCheckResult]:
            return [
                HealthCheckResult(
                    component="postgresql",
                    status=HealthStatus.HEALTHY,
                    checked_at=now,
                    latency_ms=1.0,
                )
            ]

    class FakeProviders:
        def check_all(self) -> list[HealthCheckResult]:
            return []

    service = HealthCheckService(
        infrastructure=FakeInfrastructure(),
        providers=FakeProviders(),
    )
    summary = service.check_all()
    assert summary.healthy_count == 1
    assert summary.status == HealthStatus.HEALTHY
