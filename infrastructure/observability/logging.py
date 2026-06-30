"""Structured logging formatters and filters."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from infrastructure.observability.context import context_as_log_extra


class StructuredContextFilter(logging.Filter):
    """Inject correlation context and service metadata into log records."""

    def __init__(
        self,
        *,
        service_name: str = "cast-it",
        environment: str = "development",
    ) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        record.service = self._service_name
        record.environment = self._environment
        for key, value in context_as_log_extra().items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


class StructuredJsonFormatter(logging.Formatter):
    """JSON-friendly structured log formatter."""

    def __init__(
        self,
        *,
        service_name: str = "cast-it",
        environment: str = "development",
    ) -> None:
        super().__init__()
        self._service_name = service_name
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "service": getattr(record, "service", self._service_name),
            "environment": getattr(record, "environment", self._environment),
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": getattr(record, "correlation_id", ""),
            "request_id": getattr(record, "request_id", ""),
            "job_id": getattr(record, "job_id", ""),
            "workflow_run_id": getattr(record, "workflow_run_id", ""),
            "episode_id": getattr(record, "episode_id", ""),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key in (
            "event",
            "provider",
            "step_name",
            "duration_ms",
            "retry_count",
            "error_code",
            "method",
            "path",
            "status_code",
            "task_name",
            "queue_name",
        ):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, default=str)
