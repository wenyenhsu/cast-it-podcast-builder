"""Observability API endpoint tests."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_live_health_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.django_db
def test_ready_health_endpoint(api_client: APIClient) -> None:
    with patch(
        "services.observability.health.readiness.HealthCheckService.check_all",
    ) as mock_check:
        from datetime import UTC, datetime

        from domain.observability.dtos import HealthCheckResult, HealthSummary
        from domain.observability.enums import HealthStatus

        mock_check.return_value = HealthSummary(
            status=HealthStatus.HEALTHY,
            checked_at=datetime.now(tz=UTC),
            components=[
                HealthCheckResult(
                    component="postgresql",
                    status=HealthStatus.HEALTHY,
                    checked_at=datetime.now(tz=UTC),
                    latency_ms=1.0,
                ),
                HealthCheckResult(
                    component="redis",
                    status=HealthStatus.HEALTHY,
                    checked_at=datetime.now(tz=UTC),
                    latency_ms=1.0,
                ),
                HealthCheckResult(
                    component="celery_workers",
                    status=HealthStatus.HEALTHY,
                    checked_at=datetime.now(tz=UTC),
                    latency_ms=1.0,
                ),
            ],
            healthy_count=3,
            warning_count=0,
            unhealthy_count=0,
            unknown_count=0,
        )
        response = api_client.get("/api/v1/health/ready/")
    assert response.status_code == 200
    assert response.json()["ready"] is True


@pytest.mark.django_db
def test_metrics_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/metrics/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_metrics_summary_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/metrics/summary/")
    assert response.status_code == 200
    assert "sample_count" in response.json()


@pytest.mark.django_db
def test_logs_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/logs/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_traces_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/traces/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.django_db
def test_components_health_endpoint(api_client: APIClient) -> None:
    with patch(
        "api.v1.views.observability.HealthCheckService.check_components",
        return_value=[{"component": "postgresql", "status": "healthy"}],
    ):
        response = api_client.get("/api/v1/health/components/")
    assert response.status_code == 200
    assert "components" in response.json()
