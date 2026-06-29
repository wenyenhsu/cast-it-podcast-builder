"""Tests for duplicate detection."""

import pytest

from apps.articles.models import Article, ArticleStatus
from apps.providers.models import NewsSource, ProviderType
from services.news.duplicate_detector import DuplicateDetector


@pytest.fixture
def news_source(db: None) -> NewsSource:
    return NewsSource.objects.create(
        name="Tech News",
        provider_type=ProviderType.RSS,
        rss_url="https://example.com/feed",
    )


@pytest.fixture
def duplicate_detector() -> DuplicateDetector:
    return DuplicateDetector()


@pytest.mark.django_db
class TestDuplicateDetector:
    def test_detects_duplicate_by_content_hash(
        self,
        news_source: NewsSource,
        duplicate_detector: DuplicateDetector,
    ) -> None:
        Article.objects.create(
            source=news_source,
            title="Existing",
            url="https://example.com/a",
            content_hash="abc123",
            status=ArticleStatus.COLLECTED,
        )
        assert (
            duplicate_detector.is_duplicate(
                content_hash="abc123",
                url="https://other.com",
            )
            is True
        )

    def test_detects_duplicate_by_url(
        self,
        news_source: NewsSource,
        duplicate_detector: DuplicateDetector,
    ) -> None:
        Article.objects.create(
            source=news_source,
            title="Existing",
            url="https://example.com/a",
            content_hash="abc123",
            status=ArticleStatus.COLLECTED,
        )
        assert (
            duplicate_detector.is_duplicate(
                content_hash="different",
                url="https://example.com/a",
            )
            is True
        )

    def test_non_duplicate_returns_false(
        self,
        duplicate_detector: DuplicateDetector,
    ) -> None:
        assert (
            duplicate_detector.is_duplicate(
                content_hash="unique-hash",
                url="https://example.com/new",
            )
            is False
        )
