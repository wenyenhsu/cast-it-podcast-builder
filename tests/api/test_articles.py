"""Article API tests."""

import pytest
from rest_framework.test import APIClient

from apps.articles.models import Article, ArticleStatus
from apps.providers.models import NewsSource, ProviderType
from apps.scheduler.models import Job, JobType

pytestmark = pytest.mark.django_db


@pytest.fixture
def news_source(db: None) -> NewsSource:
    return NewsSource.objects.create(
        name="Tech RSS",
        provider_type=ProviderType.RSS,
        rss_url="https://example.com/feed.xml",
        enabled=True,
    )


@pytest.fixture
def article(db: None, news_source: NewsSource) -> Article:
    return Article.objects.create(
        source=news_source,
        title="AI Breakthrough",
        url="https://example.com/ai",
        content_hash="abc123hash",
        status=ArticleStatus.COLLECTED,
    )


def test_list_articles(api_client: APIClient, article: Article) -> None:
    response = api_client.get("/api/v1/articles/")
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    assert body["results"][0]["title"] == "AI Breakthrough"


def test_retrieve_article(api_client: APIClient, article: Article) -> None:
    response = api_client.get(f"/api/v1/articles/{article.id}/")
    assert response.status_code == 200
    assert response.json()["title"] == "AI Breakthrough"


def test_create_article(api_client: APIClient, news_source: NewsSource) -> None:
    response = api_client.post(
        "/api/v1/articles/",
        {
            "source": str(news_source.id),
            "title": "New Article",
            "url": "https://example.com/new",
            "content": "Fresh content",
        },
        format="json",
    )
    assert response.status_code == 201
    assert Article.objects.filter(title="New Article").exists()


def test_filter_articles_by_status(
    api_client: APIClient,
    article: Article,
    news_source: NewsSource,
) -> None:
    Article.objects.create(
        source=news_source,
        title="Used Article",
        url="https://example.com/used",
        content_hash="usedhash123",
        status=ArticleStatus.USED,
    )
    response = api_client.get("/api/v1/articles/?status=collected")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_summarize_returns_job_accepted(
    api_client: APIClient,
    article: Article,
    mock_job_dispatch,
) -> None:
    del mock_job_dispatch
    response = api_client.post(f"/api/v1/articles/{article.id}/summarize/")
    assert response.status_code == 202
    body = response.json()
    assert "job_id" in body
    assert body["status"] == "queued"
    assert Job.objects.filter(job_type=JobType.SUMMARIZE_ARTICLE).exists()


def test_import_articles_returns_job_accepted(
    api_client: APIClient,
    mock_job_dispatch,
) -> None:
    del mock_job_dispatch
    response = api_client.post("/api/v1/articles/import/", {}, format="json")
    assert response.status_code == 202
    assert Job.objects.filter(job_type=JobType.IMPORT_NEWS).exists()
