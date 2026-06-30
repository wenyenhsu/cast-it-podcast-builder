"""Distributed tracing service."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from domain.observability.dtos import TraceSpan
from domain.observability.exceptions import TracingError
from infrastructure.observability.tracing.base import TracingBackend
from infrastructure.observability.tracing.factory import get_tracing_backend
from services.observability.settings import ObservabilitySettings

logger = logging.getLogger(__name__)


class TracingService:
    """Create and manage distributed trace spans."""

    def __init__(
        self,
        backend: TracingBackend | None = None,
        settings: ObservabilitySettings | None = None,
    ) -> None:
        self._settings = settings or ObservabilitySettings.from_django_settings()
        self._backend = backend or get_tracing_backend(
            self._settings.tracing_backend,
            enabled=self._settings.enable_tracing,
        )

    @property
    def enabled(self) -> bool:
        return self._settings.enable_tracing

    @contextmanager
    def span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
        parent_span_id: str = "",
    ) -> Iterator[TraceSpan]:
        if not self.enabled:
            yield TraceSpan(
                span_id="noop",
                trace_id="noop",
                name=name,
                start_time=self._utc_now(),
            )
            return

        active = self._backend.start_span(
            name,
            attributes=attributes,
            parent_span_id=parent_span_id,
        )
        try:
            yield active
            self._backend.end_span(active.span_id, status="ok")
        except Exception as exc:
            try:
                self._backend.end_span(
                    active.span_id,
                    status="error",
                    attributes={"error": str(exc)},
                )
            except TracingError:
                logger.warning(
                    "Failed to close trace span",
                    extra={"event": "tracing_error", "span_id": active.span_id},
                )
            raise

    def get_span(self, span_id: str) -> TraceSpan | None:
        return self._backend.get_span(span_id)

    def list_spans(
        self,
        *,
        trace_id: str = "",
        limit: int = 100,
    ) -> list[TraceSpan]:
        return self._backend.list_spans(trace_id=trace_id, limit=limit)

    def span_to_dict(self, span: TraceSpan) -> dict[str, Any]:
        return {
            "span_id": span.span_id,
            "trace_id": span.trace_id,
            "name": span.name,
            "start_time": span.start_time.isoformat(),
            "end_time": span.end_time.isoformat() if span.end_time else None,
            "duration_ms": span.duration_ms,
            "status": span.status.value,
            "attributes": span.attributes,
            "correlation_id": span.correlation_id,
            "request_id": span.request_id,
            "job_id": span.job_id,
            "workflow_run_id": span.workflow_run_id,
            "episode_id": span.episode_id,
            "parent_span_id": span.parent_span_id,
        }

    @staticmethod
    def _utc_now() -> Any:
        from datetime import UTC, datetime

        return datetime.now(tz=UTC)
