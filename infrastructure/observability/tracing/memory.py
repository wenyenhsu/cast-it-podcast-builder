"""In-memory tracing backend for development and testing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from threading import Lock

from domain.observability.dtos import TraceSpan
from domain.observability.enums import SpanStatus
from domain.observability.exceptions import TracingError
from infrastructure.observability.context import get_request_context


class InMemoryTracingBackend:
    """Thread-safe in-memory trace span storage."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._spans: dict[str, TraceSpan] = {}

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
        parent_span_id: str = "",
    ) -> TraceSpan:
        ctx = get_request_context()
        span_id = str(uuid.uuid4())
        if parent_span_id:
            parent = self._spans.get(parent_span_id)
            trace_id = parent.trace_id if parent else str(uuid.uuid4())
        else:
            trace_id = str(uuid.uuid4())
        span = TraceSpan(
            span_id=span_id,
            trace_id=trace_id,
            name=name,
            start_time=datetime.now(tz=UTC),
            attributes=dict(attributes or {}),
            correlation_id=ctx.correlation_id,
            request_id=ctx.request_id,
            job_id=ctx.job_id,
            workflow_run_id=ctx.workflow_run_id,
            episode_id=ctx.episode_id,
            parent_span_id=parent_span_id,
        )
        with self._lock:
            self._spans[span_id] = span
        return span

    def end_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        attributes: dict[str, object] | None = None,
    ) -> TraceSpan:
        with self._lock:
            span = self._spans.get(span_id)
            if span is None:
                raise TracingError(f"Span not found: {span_id}")
            end_time = datetime.now(tz=UTC)
            duration_ms = (end_time - span.start_time).total_seconds() * 1000
            merged = {**span.attributes, **dict(attributes or {})}
            updated = TraceSpan(
                span_id=span.span_id,
                trace_id=span.trace_id,
                name=span.name,
                start_time=span.start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                status=SpanStatus(status),
                attributes=merged,
                correlation_id=span.correlation_id,
                request_id=span.request_id,
                job_id=span.job_id,
                workflow_run_id=span.workflow_run_id,
                episode_id=span.episode_id,
                parent_span_id=span.parent_span_id,
            )
            self._spans[span_id] = updated
            return updated

    def get_span(self, span_id: str) -> TraceSpan | None:
        with self._lock:
            return self._spans.get(span_id)

    def list_spans(
        self,
        *,
        trace_id: str = "",
        limit: int = 100,
    ) -> list[TraceSpan]:
        with self._lock:
            spans = list(self._spans.values())
        if trace_id:
            spans = [span for span in spans if span.trace_id == trace_id]
        spans.sort(key=lambda item: item.start_time, reverse=True)
        return spans[:limit]

    def reset(self) -> None:
        with self._lock:
            self._spans.clear()
