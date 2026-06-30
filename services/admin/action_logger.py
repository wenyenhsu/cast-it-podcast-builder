"""Structured logging for Django Admin actions."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class AdminActionLogger:
    """Logs operator actions performed through Django Admin."""

    @staticmethod
    def log(
        *,
        action: str,
        user_id: int | None,
        resource_type: str,
        resource_ids: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "event": "admin_action",
            "action": action,
            "user_id": user_id,
            "resource_type": resource_type,
        }
        if resource_ids:
            payload["resource_ids"] = resource_ids
        if extra:
            payload.update(extra)
        logger.info("Admin action performed", extra=payload)
