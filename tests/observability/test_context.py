"""Correlation context propagation tests."""

from infrastructure.observability.context import (
    bind_context,
    get_correlation_id,
    get_request_context,
    get_request_id,
    reset_context,
    set_job_id,
    set_workflow_run_id,
)


def test_bind_context_generates_missing_ids() -> None:
    tokens = bind_context()
    assert get_correlation_id()
    assert get_request_id()
    reset_context(tokens)


def test_context_propagation_across_fields() -> None:
    tokens = bind_context(correlation_id="c-1", request_id="r-1")
    set_job_id("job-99")
    set_workflow_run_id("wf-99")
    ctx = get_request_context()
    assert ctx.correlation_id == "c-1"
    assert ctx.request_id == "r-1"
    assert ctx.job_id == "job-99"
    assert ctx.workflow_run_id == "wf-99"
    reset_context(tokens)
