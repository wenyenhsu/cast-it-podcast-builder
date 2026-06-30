"""API error response format tests."""

import pytest
from rest_framework.test import APIClient

from apps.providers.models import NewsSource, ProviderType

pytestmark = pytest.mark.django_db


def test_validation_error_format(api_client: APIClient, db: None) -> None:
    response = api_client.post(
        "/api/v1/news-sources/",
        {"name": ""},
        format="json",
    )
    assert response.status_code == 400
    body = response.json()
    assert body["detail"] == "Validation failed"
    assert "errors" in body


def test_not_found_format(api_client: APIClient) -> None:
    response = api_client.get("/api/v1/episodes/00000000-0000-0000-0000-000000000000/")
    assert response.status_code == 404
    assert response.json()["detail"] == "Resource not found."


def test_create_news_source(api_client: APIClient, db: None) -> None:
    response = api_client.post(
        "/api/v1/news-sources/",
        {
            "name": "Example Feed",
            "provider_type": ProviderType.RSS,
            "rss_url": "https://example.com/rss",
            "language": "en",
            "enabled": True,
        },
        format="json",
    )
    assert response.status_code == 201
    assert NewsSource.objects.filter(name="Example Feed").exists()
