"""Alert hook tests."""

import logging

import pytest

from services.observability.alerts import AlertHookRegistry, LoggingAlertHook


def test_alert_registry_emits_to_hooks(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    registry = AlertHookRegistry()
    registry.register(LoggingAlertHook())
    registry.critical_failure(
        message="Database unreachable",
        component="postgresql",
    )
    assert any(
        record.__dict__.get("event") == "alert_critical_failure"
        for record in caplog.records
    )
