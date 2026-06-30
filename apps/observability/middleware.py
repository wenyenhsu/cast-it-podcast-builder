"""Observability HTTP middleware."""

from __future__ import annotations

import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from infrastructure.observability.context import (
    bind_context,
    get_correlation_id,
    get_request_id,
)
from services.observability.logging_service import StructuredLogService
from services.observability.metrics_service import ApplicationMetricsService
from services.observability.settings import ObservabilitySettings
from services.observability.tracing_service import TracingService


class ObservabilityMiddleware:
    """Propagate correlation IDs, log requests, record metrics and traces."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response
        self._settings = ObservabilitySettings.from_django_settings()
        self._logger = StructuredLogService()
        self._metrics = ApplicationMetricsService()
        self._tracing = TracingService()

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_header = self._settings.correlation_id_header
        request_header = self._settings.request_id_header
        correlation_id = request.headers.get(correlation_header) or None
        request_id = request.headers.get(request_header) or None
        tokens = bind_context(
            correlation_id=correlation_id,
            request_id=request_id,
        )
        correlation_id_value = get_correlation_id()
        request_id_value = get_request_id()
        setattr(request, "correlation_id", correlation_id_value)
        setattr(request, "request_id", request_id_value)

        method = request.method or "UNKNOWN"
        path = request.path
        start = time.perf_counter()
        self._logger.api_request_started(method=method, path=path)

        with self._tracing.span(
            "http_request",
            attributes={"method": method, "path": path},
        ):
            response = self.get_response(request)

        duration_ms = (time.perf_counter() - start) * 1000
        self._logger.api_request_completed(
            method=method,
            path=path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        self._metrics.record_http_request(
            method=method,
            path=path,
            status_code=response.status_code,
            duration_seconds=duration_ms / 1000,
        )
        response[self._settings.correlation_id_header] = correlation_id_value
        response[self._settings.request_id_header] = request_id_value
        from infrastructure.observability.context import reset_context

        reset_context(tokens)
        return response
