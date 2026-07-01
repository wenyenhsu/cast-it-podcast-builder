"""Tests for news import service."""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus, Tag
from apps.providers.models import NewsSource, ProviderType
from domain.dtos.article import ArticleDTO
from infrastructure.news.provider_config import ProviderConfig
from infrastructure.news.providers.base import BaseNewsProvider
from services.news.import_service import NewsImportService


def _valid_dto(**overrides: object) -> ArticleDTO:
    defaults = {
        "title": "Imported Article",
        "source": "New Source",
        "url": "https://example.com/imported",
        "author": "Author",
        "published_at": timezone.now() - timedelta(hours=2),
        "language": "en",
        "category": "Tech",
        "summary": "Summary",
        "content": "Full content body",
        "tags": ["python", "django"],
    }
    defaults.update(overrides)
    return ArticleDTO(**defaults)  # type: ignore[arg-type]


class MockProvider(BaseNewsProvider):
    """Test double for BaseNewsProvider."""

    def __init__(self, articles: list[ArticleDTO]) -> None:
        config = ProviderConfig(
            source_name="Mock Source",
            provider_type="rss",
            rss_url="https://example.com/feed",
        )
        super().__init__(config)
        self._articles = articles

    def collect(self) -> list[ArticleDTO]:
        return self._articles

    def normalize(self, raw_data: object) -> list[ArticleDTO]:
        return self._articles

    def health_check(self) -> bool:
        return True


@pytest.fixture
def import_service() -> NewsImportService:
    return NewsImportService()


@pytest.mark.django_db
class TestNewsImportService:
    def test_imports_valid_articles(
        self,
        import_service: NewsImportService,
    ) -> None:
        provider = MockProvider([_valid_dto()])
        with patch("services.news.import_service.index_article_best_effort") as mock_index:
            result = import_service.import_from_provider(provider)

        assert result.imported == 1
        assert result.skipped_duplicates == 0
        assert result.skipped_invalid == 0
        assert result.created_sources == 1
        assert Article.objects.count() == 1
        assert NewsSource.objects.filter(name="New Source").exists()
        assert Tag.objects.filter(name="python").exists()
        mock_index.assert_called_once()

    def test_skips_invalid_articles(
        self,
        import_service: NewsImportService,
    ) -> None:
        provider = MockProvider([_valid_dto(title="")])
        result = import_service.import_from_provider(provider)

        assert result.imported == 0
        assert result.skipped_invalid == 1
        assert Article.objects.count() == 0

    def test_skips_duplicate_articles(
        self,
        import_service: NewsImportService,
    ) -> None:
        source = NewsSource.objects.create(
            name="Existing Source",
            provider_type=ProviderType.RSS,
        )
        hash_service = import_service._hash_service
        content_hash = hash_service.generate_hash("Full content body")
        Article.objects.create(
            source=source,
            title="Existing",
            url="https://example.com/imported",
            content_hash=content_hash,
            status=ArticleStatus.COLLECTED,
        )

        provider = MockProvider([_valid_dto()])
        result = import_service.import_from_provider(provider)

        assert result.imported == 0
        assert result.skipped_duplicates == 1
        assert Article.objects.count() == 1

    def test_creates_missing_news_source(
        self,
        import_service: NewsImportService,
    ) -> None:
        provider = MockProvider([_valid_dto(source="Auto Created Source")])
        result = import_service.import_from_provider(provider)

        assert result.created_sources == 1
        source = NewsSource.objects.get(name="Auto Created Source")
        assert source.provider_type == ProviderType.RSS
        assert source.enabled is True

    def test_handles_provider_collection_error(
        self,
        import_service: NewsImportService,
    ) -> None:
        provider = MagicMock(spec=BaseNewsProvider)
        provider.source_name = "Broken"
        provider.__class__.__name__ = "RSSProvider"
        provider.collect.side_effect = RuntimeError("Feed unavailable")

        result = import_service.import_from_provider(provider)

        assert result.imported == 0
        assert len(result.errors) == 1
        assert "Feed unavailable" in result.errors[0]
