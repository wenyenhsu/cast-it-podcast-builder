"""Tests for core application."""

import pytest
from django.test import Client


@pytest.mark.django_db
def test_django_setup() -> None:
    """Verify Django test database is accessible."""
    assert True


def test_health_check(api_client: Client) -> None:
    """Verify the health check endpoint returns ok."""
    response = api_client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
