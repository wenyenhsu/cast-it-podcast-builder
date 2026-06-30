"""Structured logging helpers for workflow operations."""

from typing import Any

from infrastructure.observability.context import context_as_log_extra, set_workflow_run_id
from services.observability.logging_service import StructuredLogService

_log = StructuredLogService()


def log_workflow_event(event: str, **extra: Any) -> None:
    """Emit a structured workflow log entry."""
    workflow_run_id = extra.get("workflow_run_id")
    if workflow_run_id:
        try:
            set_workflow_run_id(str(workflow_run_id))
        except Exception:
            pass
    payload = {**context_as_log_extra(), **extra}
    _log.info("Workflow event", event=event, **payload)
