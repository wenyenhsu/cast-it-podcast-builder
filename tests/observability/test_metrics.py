"""Metrics collection tests."""

from infrastructure.observability.metrics.memory import InMemoryMetricsBackend
from services.observability.metrics_service import (
    ApplicationMetricsService,
    MetricNames,
)


def test_metrics_increment_and_observe() -> None:
    backend = InMemoryMetricsBackend()
    service = ApplicationMetricsService(backend=backend)
    service.increment(MetricNames.HTTP_REQUEST_COUNT, labels={"method": "GET"})
    service.observe(
        MetricNames.HTTP_REQUEST_LATENCY,
        0.25,
        labels={"method": "GET"},
    )
    samples = backend.export()
    assert len(samples) >= 2


def test_record_http_request_increments_error_on_500() -> None:
    backend = InMemoryMetricsBackend()
    service = ApplicationMetricsService(backend=backend)
    service.record_http_request(
        method="GET",
        path="/api/v1/health/",
        status_code=500,
        duration_seconds=0.1,
    )
    exported = service.export()
    names = {sample["name"] for sample in exported}
    assert MetricNames.HTTP_REQUEST_COUNT in names
    assert MetricNames.HTTP_ERROR_COUNT in names


def test_prometheus_export_format() -> None:
    backend = InMemoryMetricsBackend()
    service = ApplicationMetricsService(backend=backend)
    service.increment("test_counter_total")
    output = service.export_prometheus()
    assert "test_counter_total" in output
