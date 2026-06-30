"""Tests for news source dashboard service."""

import pytest

from apps.articles.models import Article, ArticleStatus
from apps.providers.models import NewsSource, ProviderType
from services.admin.news_sources import NewsSourceDashboardService, NewsSourceFormError


@pytest.mark.django_db
def test_create_rss_source_with_import_limit(news_source: NewsSource) -> None:
    del news_source
    service = NewsSourceDashboardService()
    source = service.create_rss_source(
        name="Limited Feed",
        rss_url="https://example.com/limited.xml",
        max_articles_per_import=3,
    )
    assert source.max_articles_per_import == 3


@pytest.mark.django_db
def test_create_manual_article(news_source: NewsSource) -> None:
    del news_source
    service = NewsSourceDashboardService()
    manual_source = service.get_or_create_manual_source()
    article = service.create_manual_article(
        source_id=str(manual_source.id),
        title="Handwritten Story",
        content="Full body text for the podcast pipeline.",
        author="Editor",
    )
    assert article.source.provider_type == ProviderType.MANUAL
    assert article.status == ArticleStatus.COLLECTED
    assert Article.objects.filter(title="Handwritten Story").exists()


@pytest.mark.django_db
def test_create_manual_article_rejects_duplicate_content() -> None:
    service = NewsSourceDashboardService()
    manual_source = service.get_or_create_manual_source()
    service.create_manual_article(
        source_id=str(manual_source.id),
        title="First",
        content="Same body",
    )
    with pytest.raises(NewsSourceFormError):
        service.create_manual_article(
            source_id=str(manual_source.id),
            title="Second",
            content="Same body",
        )


@pytest.mark.django_db
def test_create_rss_source_requires_valid_url() -> None:
    service = NewsSourceDashboardService()
    with pytest.raises(NewsSourceFormError):
        service.create_rss_source(name="Bad", rss_url="not-a-url")


@pytest.mark.django_db
def test_list_sources_includes_article_count(news_source: NewsSource) -> None:
    Article.objects.create(
        title="Sample",
        source=news_source,
        url="https://example.com/a",
        content_hash="hash-1",
        status=ArticleStatus.COLLECTED,
    )
    rows = NewsSourceDashboardService().list_sources()
    assert rows[0]["article_count"] == 1
