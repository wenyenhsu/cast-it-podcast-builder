"""Structured logging tests."""

import json
import logging

import pytest

from infrastructure.observability.context import bind_context, reset_context
from infrastructure.observability.logging import (
    StructuredContextFilter,
    StructuredJsonFormatter,
)
from services.observability.logging_service import StructuredLogService


def test_json_formatter_includes_context_fields() -> None:
    tokens = bind_context(correlation_id="corr-1", request_id="req-1")
    formatter = StructuredJsonFormatter(service_name="test-service", environment="test")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    StructuredContextFilter(service_name="test-service", environment="test").filter(
        record
    )
    payload = json.loads(formatter.format(record))
    assert payload["message"] == "Test message"
    assert payload["service"] == "test-service"
    assert payload["environment"] == "test"
    assert payload["correlation_id"] == "corr-1"
    assert payload["request_id"] == "req-1"
    reset_context(tokens)


def test_structured_log_service_emits_event(caplog: pytest.LogCaptureFixture) -> None:
    logger = logging.getLogger("cast_it.observability")
    logger.addHandler(caplog.handler)
    try:
        tokens = bind_context(correlation_id="corr-2", request_id="req-2")
        service = StructuredLogService()
        service.info("Job started", event="job_started", job_id="job-1")
        assert any(
            record.__dict__.get("event") == "job_started" for record in caplog.records
        )
        reset_context(tokens)
    finally:
        logger.removeHandler(caplog.handler)
