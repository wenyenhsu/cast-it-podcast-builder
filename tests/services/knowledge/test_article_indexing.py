"""Tests for best-effort article indexing."""

from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.articles.models import Article, ArticleStatus
from apps.providers.models import NewsSource, ProviderType
from domain.knowledge.dtos import IndexResult
from services.knowledge.article_indexing import (
    index_article_best_effort,
    index_articles_best_effort,
    is_rag_enabled,
)


@pytest.mark.django_db
@override_settings(RAG_ENABLED=False)
def test_index_article_skips_when_disabled(news_source: NewsSource) -> None:
    article = Article.objects.create(
        source=news_source,
        title="Disabled",
        url="https://example.com/disabled",
        content="Body",
        status=ArticleStatus.COLLECTED,
    )
    assert index_article_best_effort(article) is None


@pytest.mark.django_db
@override_settings(RAG_ENABLED=True)
def test_index_article_calls_indexing_service(news_source: NewsSource) -> None:
    article = Article.objects.create(
        source=news_source,
        title="Indexed",
        url="https://example.com/indexed",
        content="Body",
        status=ArticleStatus.COLLECTED,
    )
    with patch("services.knowledge.article_indexing.IndexingService") as mock_service:
        mock_service.return_value.index_document.return_value = IndexResult(
            document_id="doc-1",
            chunks_created=2,
            embeddings_generated=2,
        )
        result = index_article_best_effort(article)

    assert result is not None
    assert result.chunks_created == 2
    mock_service.return_value.index_document.assert_called_once()


@pytest.mark.django_db
@override_settings(RAG_ENABLED=True)
def test_index_article_returns_none_on_failure(news_source: NewsSource) -> None:
    article = Article.objects.create(
        source=news_source,
        title="Failed",
        url="https://example.com/failed",
        content="Body",
        status=ArticleStatus.COLLECTED,
    )
    with patch("services.knowledge.article_indexing.IndexingService") as mock_service:
        mock_service.return_value.index_document.side_effect = RuntimeError("boom")
        assert index_article_best_effort(article) is None


@pytest.mark.django_db
@override_settings(RAG_ENABLED=True)
def test_index_articles_best_effort_counts_successes(news_source: NewsSource) -> None:
    articles = [
        Article.objects.create(
            source=news_source,
            title=f"Article {index}",
            url=f"https://example.com/{index}",
            content=f"Body {index}",
            content_hash=f"hash-{index}",
            status=ArticleStatus.COLLECTED,
        )
        for index in range(2)
    ]
    with patch(
        "services.knowledge.article_indexing.index_article_best_effort",
        side_effect=[IndexResult("1", 1, 1), None],
    ):
        assert index_articles_best_effort(articles) == 1


def test_is_rag_enabled_reads_settings() -> None:
    with override_settings(RAG_ENABLED=True):
        assert is_rag_enabled() is True
    with override_settings(RAG_ENABLED=False):
        assert is_rag_enabled() is False
