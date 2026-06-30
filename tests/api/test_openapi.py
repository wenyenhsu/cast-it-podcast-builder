"""OpenAPI schema generation tests."""

import json

import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_openapi_schema_endpoint(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/schema/?format=json")
    assert response.status_code == 200
    schema = json.loads(response.content)
    assert schema["info"]["title"] == "Cast It Podcast Generator API"
    paths = schema["paths"]
    assert "/api/v1/articles/" in paths
    assert "/api/v1/episodes/" in paths
    assert "/api/v1/jobs/" in paths


def test_swagger_ui_available(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/docs/")
    assert response.status_code == 200


def test_redoc_available(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/redoc/")
    assert response.status_code == 200
