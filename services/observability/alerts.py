"""Alert hook interface for future integrations."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class AlertHook(Protocol):
    """Protocol for external alert integrations."""

    def notify(self, event_type: str, payload: dict[str, Any]) -> None:
        """Send an alert notification."""


@dataclass
class AlertHookRegistry:
    """Registry of alert hooks for operational events."""

    hooks: list[AlertHook] = field(default_factory=list)

    def register(self, hook: AlertHook) -> None:
        self.hooks.append(hook)

    def emit(self, event_type: str, payload: dict[str, Any]) -> None:
        for hook in self.hooks:
            try:
                hook.notify(event_type, payload)
            except Exception as exc:
                logger.warning(
                    "Alert hook failed",
                    extra={
                        "event": "alert_hook_failed",
                        "alert_event": event_type,
                        "error": str(exc),
                    },
                )

    def critical_failure(self, *, message: str, **payload: Any) -> None:
        self.emit("critical_failure", {"message": message, **payload})

    def health_degradation(
        self,
        *,
        component: str,
        status: str,
        **payload: Any,
    ) -> None:
        self.emit(
            "health_degradation",
            {"component": component, "status": status, **payload},
        )

    def repeated_retries(
        self,
        *,
        resource_type: str,
        resource_id: str,
        retry_count: int,
        **payload: Any,
    ) -> None:
        self.emit(
            "repeated_retries",
            {
                "resource_type": resource_type,
                "resource_id": resource_id,
                "retry_count": retry_count,
                **payload,
            },
        )

    def provider_outage(self, *, provider: str, **payload: Any) -> None:
        self.emit("provider_outage", {"provider": provider, **payload})

    def stuck_workflow(self, *, workflow_run_id: str, **payload: Any) -> None:
        self.emit("stuck_workflow", {"workflow_run_id": workflow_run_id, **payload})

    def publish_failure(self, *, episode_id: str, **payload: Any) -> None:
        self.emit("publish_failure", {"episode_id": episode_id, **payload})

    def worker_down(self, **payload: Any) -> None:
        self.emit("worker_down", payload)


class LoggingAlertHook:
    """Default alert hook that writes structured log entries."""

    def notify(self, event_type: str, payload: dict[str, Any]) -> None:
        logger.error(
            f"Alert: {event_type}",
            extra={
                "event": f"alert_{event_type}",
                "alert_message": payload.get("message", ""),
                **{k: v for k, v in payload.items() if k != "message"},
            },
        )


_default_registry: AlertHookRegistry | None = None


def get_alert_registry() -> AlertHookRegistry:
    global _default_registry
    if _default_registry is None:
        registry = AlertHookRegistry()
        registry.register(LoggingAlertHook())
        _default_registry = registry
    return _default_registry


def reset_alert_registry() -> None:
    global _default_registry
    _default_registry = None
