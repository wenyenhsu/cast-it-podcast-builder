"""Structured logging helpers for workflow operations."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def log_workflow_event(event: str, **extra: Any) -> None:
    """Emit a structured workflow log entry."""
    payload = {"event": event, **extra}
    logger.info("Workflow event", extra=payload)
