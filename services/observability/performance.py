"""Performance duration tracking helpers."""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from services.observability.metrics_service import ApplicationMetricsService


@dataclass
class DurationStats:
    """Aggregated duration statistics."""

    count: int = 0
    total_ms: float = 0.0
    min_ms: float | None = None
    max_ms: float | None = None
    values_ms: list[float] = field(default_factory=list)

    @property
    def avg_ms(self) -> float:
        if self.count == 0:
            return 0.0
        return self.total_ms / self.count

    def percentile(self, pct: float) -> float | None:
        if not self.values_ms:
            return None
        ordered = sorted(self.values_ms)
        index = int((pct / 100) * (len(ordered) - 1))
        return ordered[index]


class PerformanceTracker:
    """Track operation durations and optionally record metrics."""

    def __init__(
        self,
        metrics: ApplicationMetricsService | None = None,
    ) -> None:
        self._metrics = metrics or ApplicationMetricsService()
        self._lock = Lock()
        self._stats: dict[str, DurationStats] = defaultdict(DurationStats)

    @contextmanager
    def track(
        self,
        operation: str,
        *,
        metric_name: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            self._record(operation, duration_ms)
            if metric_name:
                self._metrics.observe(
                    metric_name,
                    duration_ms / 1000,
                    labels=labels,
                )

    def _record(self, operation: str, duration_ms: float) -> None:
        with self._lock:
            stats = self._stats[operation]
            stats.count += 1
            stats.total_ms += duration_ms
            stats.values_ms.append(duration_ms)
            stats.min_ms = (
                duration_ms if stats.min_ms is None else min(stats.min_ms, duration_ms)
            )
            stats.max_ms = (
                duration_ms if stats.max_ms is None else max(stats.max_ms, duration_ms)
            )

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                operation: {
                    "count": stats.count,
                    "avg_ms": round(stats.avg_ms, 2),
                    "min_ms": stats.min_ms,
                    "max_ms": stats.max_ms,
                    "p50_ms": stats.percentile(50),
                    "p95_ms": stats.percentile(95),
                    "p99_ms": stats.percentile(99),
                }
                for operation, stats in self._stats.items()
            }

    def reset(self) -> None:
        with self._lock:
            self._stats.clear()
