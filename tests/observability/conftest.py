"""Observability test fixtures."""

import pytest

from infrastructure.observability.metrics.factory import reset_metrics_backend
from infrastructure.observability.tracing.factory import reset_tracing_backend
from services.observability.alerts import reset_alert_registry


@pytest.fixture(autouse=True)
def reset_observability_backends() -> None:
    reset_metrics_backend()
    reset_tracing_backend()
    reset_alert_registry()
