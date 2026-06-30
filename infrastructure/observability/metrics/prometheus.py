"""Prometheus-style metrics backend."""

from __future__ import annotations

from infrastructure.observability.metrics.memory import InMemoryMetricsBackend


class PrometheusMetricsBackend(InMemoryMetricsBackend):
    """Prometheus exposition backend backed by in-memory storage."""

    def export_prometheus(self) -> str:
        return super().export_prometheus()
