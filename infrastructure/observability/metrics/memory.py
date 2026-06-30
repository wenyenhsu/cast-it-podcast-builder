"""In-memory metrics backend for development and testing."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from threading import Lock

from domain.observability.dtos import MetricSample


def _label_key(labels: dict[str, str] | None) -> tuple[tuple[str, str], ...]:
    if not labels:
        return ()
    return tuple(sorted(labels.items()))


class InMemoryMetricsBackend:
    """Thread-safe in-memory metrics collector."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = (
            defaultdict(float)
        )
        self._observations: dict[
            tuple[str, tuple[tuple[str, str], ...]], list[float]
        ] = defaultdict(list)

    def increment(
        self,
        name: str,
        *,
        value: float = 1.0,
        labels: dict[str, str] | None = None,
    ) -> None:
        key = (name, _label_key(labels))
        with self._lock:
            self._counters[key] += value

    def observe(
        self,
        name: str,
        value: float,
        *,
        labels: dict[str, str] | None = None,
    ) -> None:
        key = (name, _label_key(labels))
        with self._lock:
            self._observations[key].append(value)

    def export(self) -> list[MetricSample]:
        now = datetime.now(tz=UTC)
        samples: list[MetricSample] = []
        with self._lock:
            for (name, label_tuple), total in self._counters.items():
                labels = dict(label_tuple)
                samples.append(
                    MetricSample(name=name, value=total, labels=labels, timestamp=now)
                )
            for (name, label_tuple), values in self._observations.items():
                labels = dict(label_tuple)
                for value in values:
                    samples.append(
                        MetricSample(
                            name=f"{name}_observation",
                            value=value,
                            labels=labels,
                            timestamp=now,
                        )
                    )
        return samples

    def export_prometheus(self) -> str:
        lines: list[str] = []
        with self._lock:
            for (name, label_tuple), total in self._counters.items():
                label_str = _prometheus_labels(label_tuple)
                lines.append(f"{name}{label_str} {total}")
            for (name, label_tuple), values in self._observations.items():
                label_str = _prometheus_labels(label_tuple)
                metric_name = f"{name}_count"
                lines.append(f"{metric_name}{label_str} {len(values)}")
                if values:
                    metric_sum = f"{name}_sum"
                    lines.append(f"{metric_sum}{label_str} {sum(values)}")
        return "\n".join(lines) + ("\n" if lines else "")

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._observations.clear()


def _prometheus_labels(label_tuple: tuple[tuple[str, str], ...]) -> str:
    if not label_tuple:
        return ""
    parts = [f'{key}="{value}"' for key, value in label_tuple]
    return "{" + ",".join(parts) + "}"
