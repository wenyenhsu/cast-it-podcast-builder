"""Observability middleware tests."""

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from apps.observability.middleware import ObservabilityMiddleware


@pytest.mark.django_db
def test_middleware_sets_response_headers() -> None:
    factory = RequestFactory()
    request = factory.get("/api/v1/health/live/")

    def get_response(req: object) -> HttpResponse:
        del req
        return HttpResponse("ok", status=200)

    middleware = ObservabilityMiddleware(get_response)
    response = middleware(request)
    assert response["X-Correlation-ID"]
    assert response["X-Request-ID"]


@pytest.mark.django_db
def test_middleware_propagates_incoming_headers() -> None:
    factory = RequestFactory()
    request = factory.get(
        "/api/v1/health/live/",
        HTTP_X_CORRELATION_ID="incoming-corr",
        HTTP_X_REQUEST_ID="incoming-req",
    )

    def get_response(req: object) -> HttpResponse:
        del req
        return HttpResponse("ok", status=200)

    response = ObservabilityMiddleware(get_response)(request)
    assert response["X-Correlation-ID"] == "incoming-corr"
    assert response["X-Request-ID"] == "incoming-req"
