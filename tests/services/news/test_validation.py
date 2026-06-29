"""Tests for article validation."""

from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone

from domain.dtos.article import ArticleDTO
from services.news.validation import ArticleValidator


@pytest.fixture
def validator() -> ArticleValidator:
    return ArticleValidator()


def _make_dto(**overrides: object) -> ArticleDTO:
    defaults = {
        "title": "Valid Title",
        "source": "Test Source",
        "url": "https://example.com/article",
        "published_at": timezone.now() - timedelta(hours=1),
    }
    defaults.update(overrides)
    return ArticleDTO(**defaults)  # type: ignore[arg-type]


class TestArticleValidator:
    def test_valid_article_passes(self, validator: ArticleValidator) -> None:
        result = validator.validate(_make_dto())
        assert result.is_valid is True
        assert result.errors == []

    def test_empty_title_is_rejected(self, validator: ArticleValidator) -> None:
        result = validator.validate(_make_dto(title="   "))
        assert result.is_valid is False
        assert "Title must not be empty." in result.errors

    def test_missing_url_is_rejected(self, validator: ArticleValidator) -> None:
        result = validator.validate(_make_dto(url=""))
        assert result.is_valid is False
        assert "URL is required." in result.errors

    def test_future_publish_date_is_rejected(
        self,
        validator: ArticleValidator,
    ) -> None:
        future = timezone.now() + timedelta(days=1)
        result = validator.validate(_make_dto(published_at=future))
        assert result.is_valid is False
        assert "Published date is invalid." in result.errors

    def test_naive_publish_date_is_rejected(
        self,
        validator: ArticleValidator,
    ) -> None:
        naive = datetime(2024, 1, 1, 12, 0, 0)
        result = validator.validate(_make_dto(published_at=naive))
        assert result.is_valid is False
        assert "Published date is invalid." in result.errors

    def test_missing_publish_date_is_allowed(
        self,
        validator: ArticleValidator,
    ) -> None:
        result = validator.validate(_make_dto(published_at=None))
        assert result.is_valid is True

    def test_valid_timezone_aware_date_passes(
        self,
        validator: ArticleValidator,
    ) -> None:
        past = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        result = validator.validate(_make_dto(published_at=past))
        assert result.is_valid is True
