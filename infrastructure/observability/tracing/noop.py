"""No-op tracing backend when tracing is disabled."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from domain.observability.dtos import TraceSpan
from domain.observability.enums import SpanStatus


class NoOpTracingBackend:
    """Tracing backend that discards span storage."""

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
        parent_span_id: str = "",
    ) -> TraceSpan:
        del attributes, parent_span_id
        now = datetime.now(tz=UTC)
        span_id = str(uuid.uuid4())
        return TraceSpan(
            span_id=span_id,
            trace_id=span_id,
            name=name,
            start_time=now,
        )

    def end_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        attributes: dict[str, object] | None = None,
    ) -> TraceSpan:
        del attributes
        now = datetime.now(tz=UTC)
        return TraceSpan(
            span_id=span_id,
            trace_id=span_id,
            name="noop",
            start_time=now,
            end_time=now,
            duration_ms=0.0,
            status=SpanStatus(status),
        )

    def get_span(self, span_id: str) -> TraceSpan | None:
        del span_id
        return None

    def list_spans(
        self,
        *,
        trace_id: str = "",
        limit: int = 100,
    ) -> list[TraceSpan]:
        del trace_id, limit
        return []

    def reset(self) -> None:
        return None
