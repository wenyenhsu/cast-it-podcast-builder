"""Deployment API and management command tests."""

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_version_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/version/")
    assert response.status_code == 200
    payload = response.json()
    assert "version" in payload
    assert "git_commit" in payload
    assert "build_number" in payload
    assert "environment" in payload


@pytest.mark.django_db
def test_validate_config_command_warn_only(
    production_env: None,
) -> None:
    call_command("validate_config", warn_only=True)


@pytest.mark.django_db
def test_live_health_endpoint_for_startup(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/health/live/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
