"""Distributed tracing tests."""

from infrastructure.observability.tracing.memory import InMemoryTracingBackend
from services.observability.tracing_service import TracingService


def test_span_records_duration() -> None:
    backend = InMemoryTracingBackend()
    tracing = TracingService(backend=backend)
    with tracing.span("workflow_step", attributes={"step": "generate_script"}) as span:
        assert span.span_id
    finished = backend.get_span(span.span_id)
    assert finished is not None
    assert finished.duration_ms is not None
    assert finished.status.value == "ok"


def test_list_and_get_span() -> None:
    backend = InMemoryTracingBackend()
    tracing = TracingService(backend=backend)
    with tracing.span("provider_call"):
        pass
    spans = tracing.list_spans(limit=10)
    assert len(spans) == 1
    detail = tracing.get_span(spans[0].span_id)
    assert detail is not None
