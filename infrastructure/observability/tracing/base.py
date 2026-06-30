"""Tracing backend abstractions."""

from __future__ import annotations

from typing import Protocol

from domain.observability.dtos import TraceSpan


class TracingBackend(Protocol):
    """Protocol for pluggable distributed tracing backends."""

    def start_span(
        self,
        name: str,
        *,
        attributes: dict[str, object] | None = None,
        parent_span_id: str = "",
    ) -> TraceSpan:
        """Start a new trace span."""

    def end_span(
        self,
        span_id: str,
        *,
        status: str = "ok",
        attributes: dict[str, object] | None = None,
    ) -> TraceSpan:
        """Finish an active span."""

    def get_span(self, span_id: str) -> TraceSpan | None:
        """Return a span by identifier."""

    def list_spans(
        self,
        *,
        trace_id: str = "",
        limit: int = 100,
    ) -> list[TraceSpan]:
        """Return recent spans."""

    def reset(self) -> None:
        """Clear stored spans (primarily for tests)."""
