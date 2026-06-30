"""Shared API view mixins."""

import logging
from typing import Any

from rest_framework.request import Request

from infrastructure.observability.context import context_as_log_extra
from services.observability.logging_service import StructuredLogService

logger = logging.getLogger(__name__)
_structured = StructuredLogService()


class RequestLoggingMixin:
    """Log API requests with structured metadata."""

    resource_name: str = "resource"

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        _structured.info(
            "API endpoint hit",
            event="api_endpoint_hit",
            resource=self.resource_name,
            method=request.method,
            path=request.path,
            **context_as_log_extra(),
        )

    def log_action(
        self,
        *,
        action: str,
        resource_id: str | None = None,
        job_id: str | None = None,
        status_code: int | None = None,
    ) -> None:
        extra: dict[str, Any] = {
            "resource": self.resource_name,
            "action": action,
            **context_as_log_extra(),
        }
        if resource_id:
            extra["resource_id"] = resource_id
        if job_id:
            extra["job_id"] = job_id
        if status_code:
            extra["status_code"] = status_code
        _structured.info("API action requested", event="api_action", **extra)
