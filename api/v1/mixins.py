"""Shared API view mixins."""

import logging
from typing import Any

from rest_framework.request import Request

logger = logging.getLogger(__name__)


class RequestLoggingMixin:
    """Log API requests with structured metadata."""

    resource_name: str = "resource"

    def initial(self, request: Request, *args: Any, **kwargs: Any) -> None:
        super().initial(request, *args, **kwargs)
        logger.info(
            "API endpoint hit",
            extra={
                "event": "api_endpoint_hit",
                "resource": self.resource_name,
                "method": request.method,
                "path": request.path,
            },
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
            "event": "api_action",
            "resource": self.resource_name,
            "action": action,
        }
        if resource_id:
            extra["resource_id"] = resource_id
        if job_id:
            extra["job_id"] = job_id
        if status_code:
            extra["status_code"] = status_code
        logger.info("API action requested", extra=extra)
