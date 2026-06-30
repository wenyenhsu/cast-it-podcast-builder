"""Legacy health smoke tests."""

from unittest.mock import patch

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
def test_django_setup() -> None:
    assert True


@pytest.mark.django_db
def test_health_check(api_client: APIClient) -> None:
    with patch(
        "api.v1.services.health.ApiHealthService.overall",
        return_value={"status": "ok", "checks": {}},
    ):
        response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
