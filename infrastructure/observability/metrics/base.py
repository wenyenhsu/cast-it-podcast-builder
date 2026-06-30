"""Metrics backend abstractions."""

from __future__ import annotations

from typing import Protocol

from domain.observability.dtos import MetricSample


class MetricsBackend(Protocol):
    """Protocol for pluggable metrics storage backends."""

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a counter increment."""

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        """Record a histogram or gauge observation."""

    def export(self) -> list[MetricSample]:
        """Return collected metric samples."""

    def export_prometheus(self) -> str:
        """Return Prometheus text exposition format."""

    def reset(self) -> None:
        """Clear stored metrics (primarily for tests)."""
