"""API health endpoint tests."""

from contextlib import contextmanager
from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@contextmanager
def patch_health_services():
    with (
        patch(
            "api.v1.services.health.CeleryHealthService.check_all",
            return_value={"healthy": True, "redis": True, "workers": True},
        ),
        patch(
            "api.v1.services.health.LLMProviderFactory.create",
        ) as llm_factory,
        patch(
            "api.v1.services.health.TTSProviderFactory.create",
        ) as tts_factory,
        patch(
            "api.v1.services.health.PublisherFactory.enabled_publishers",
            return_value={},
        ),
    ):
        llm_provider = llm_factory.return_value
        llm_provider.health_check.return_value = True
        tts_provider = tts_factory.return_value
        tts_provider.health_check.return_value = True
        yield


@pytest.mark.django_db
def test_health_endpoint(api_client: APIClient) -> None:
    with patch_health_services():
        response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "checks" in response.json()


@pytest.mark.django_db
def test_celery_health_endpoint(api_client: APIClient) -> None:
    with patch_health_services():
        response = api_client.get("/api/v1/health/celery/")
    assert response.status_code == 200
    assert "healthy" in response.json()
