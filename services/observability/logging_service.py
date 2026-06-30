"""Structured logging service."""

from __future__ import annotations

import logging
from typing import Any

from infrastructure.observability.context import context_as_log_extra

logger = logging.getLogger("cast_it.observability")


class StructuredLogService:
    """Emit structured logs enriched with correlation context."""

    def log(
        self,
        level: str,
        message: str,
        *,
        event: str,
        **extra: Any,
    ) -> None:
        payload = {"event": event, **context_as_log_extra(), **extra}
        log_method = getattr(logger, level.lower(), logger.info)
        log_method(message, extra=payload)

    def debug(self, message: str, *, event: str, **extra: Any) -> None:
        self.log("debug", message, event=event, **extra)

    def info(self, message: str, *, event: str, **extra: Any) -> None:
        self.log("info", message, event=event, **extra)

    def warning(self, message: str, *, event: str, **extra: Any) -> None:
        self.log("warning", message, event=event, **extra)

    def error(self, message: str, *, event: str, **extra: Any) -> None:
        self.log("error", message, event=event, **extra)

    def critical(self, message: str, *, event: str, **extra: Any) -> None:
        self.log("critical", message, event=event, **extra)

    def api_request_started(
        self,
        *,
        method: str,
        path: str,
        **extra: Any,
    ) -> None:
        self.info(
            "API request started",
            event="api_request_started",
            method=method,
            path=path,
            **extra,
        )

    def api_request_completed(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        **extra: Any,
    ) -> None:
        self.info(
            "API request completed",
            event="api_request_completed",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            **extra,
        )

    def job_event(self, event: str, *, job_id: str, **extra: Any) -> None:
        self.info(f"Job {event}", event=event, job_id=job_id, **extra)

    def workflow_step_event(
        self,
        event: str,
        *,
        workflow_run_id: str,
        step_name: str,
        **extra: Any,
    ) -> None:
        self.info(
            f"Workflow step {event}",
            event=event,
            workflow_run_id=workflow_run_id,
            step_name=step_name,
            **extra,
        )

    def provider_event(
        self,
        event: str,
        *,
        provider: str,
        duration_ms: float | None = None,
        **extra: Any,
    ) -> None:
        payload = {"provider": provider, **extra}
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        self.info(f"Provider {event}", event=event, **payload)
