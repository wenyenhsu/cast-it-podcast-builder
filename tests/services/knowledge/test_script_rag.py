"""Tests for script-generation RAG enrichment."""

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeStatus
from domain.knowledge.dtos import AssembledContext, ContextBlock
from services.knowledge.script_rag import ScriptRagService


@pytest.mark.django_db
@override_settings(RAG_ENABLED=False)
def test_enrich_returns_disabled_result(news_source) -> None:
    article = Article.objects.create(
        source=news_source,
        title="Story",
        url="https://example.com/story",
        content="Body",
        status=ArticleStatus.SELECTED,
    )
    episode = Episode.objects.create(
        title="Weekly AI News",
        summary="Top stories",
        language="en",
        status=EpisodeStatus.DRAFT,
    )
    episode.articles.add(article)

    result = ScriptRagService().enrich(episode, [article])

    assert result.enabled is False
    assert result.context_text == ""
    assert result.chunks_used == 0


@pytest.mark.django_db
@override_settings(RAG_ENABLED=True)
def test_enrich_includes_retrieved_context(news_source) -> None:
    article = Article.objects.create(
        source=news_source,
        title="Story",
        url="https://example.com/story",
        content="Body",
        status=ArticleStatus.SELECTED,
    )
    episode = Episode.objects.create(
        title="Weekly AI News",
        summary="Top stories",
        language="en",
        status=EpisodeStatus.DRAFT,
    )
    episode.articles.add(article)

    context_builder = MagicMock()
    context_builder.build.return_value = AssembledContext(
        query="Weekly AI News",
        blocks=[
            ContextBlock(
                chunk_id="chunk-1",
                title="Related story",
                text="Vector-retrieved excerpt.",
                score=0.9,
                token_count=12,
                source_type="article",
                source_id=str(article.id),
            )
        ],
        context_text="[article:1] Related story\nVector-retrieved excerpt.",
        total_tokens=12,
        chunks_retrieved=1,
        chunks_used=1,
    )

    with patch(
        "services.knowledge.script_rag.index_articles_best_effort",
        return_value=1,
    ):
        result = ScriptRagService(context_builder=context_builder).enrich(
            episode,
            [article],
        )

    assert result.enabled is True
    assert result.chunks_used == 1
    assert "Vector-retrieved excerpt." in result.context_text
    context_builder.build.assert_called_once()


@pytest.mark.django_db
@override_settings(RAG_ENABLED=True)
def test_enrich_gracefully_handles_retrieval_failure(news_source) -> None:
    from domain.knowledge.exceptions import RetrievalError

    article = Article.objects.create(
        source=news_source,
        title="Story",
        url="https://example.com/story",
        content="Body",
        status=ArticleStatus.SELECTED,
    )
    episode = Episode.objects.create(
        title="Weekly AI News",
        summary="Top stories",
        language="en",
        status=EpisodeStatus.DRAFT,
    )
    episode.articles.add(article)

    context_builder = MagicMock()
    context_builder.build.side_effect = RetrievalError("embedding unavailable")

    with patch(
        "services.knowledge.script_rag.index_articles_best_effort",
        return_value=0,
    ):
        result = ScriptRagService(context_builder=context_builder).enrich(
            episode,
            [article],
        )

    assert result.enabled is True
    assert result.context_text == ""
    assert result.chunks_used == 0


@pytest.mark.django_db
@override_settings(RAG_ENABLED=True)
def test_enrich_article_filters_by_source_id(news_source) -> None:
    article = Article.objects.create(
        source=news_source,
        title="One article only",
        url="https://example.com/one-article",
        summary="Article summary",
        content="Long article body",
        status=ArticleStatus.SELECTED,
    )
    episode = Episode.objects.create(
        title="Weekly AI News",
        summary="Top stories",
        language="zh-TW",
        status=EpisodeStatus.DRAFT,
    )
    context_builder = MagicMock()
    context_builder.build.return_value = AssembledContext(
        query=article.title,
        blocks=[],
        context_text="Article-specific excerpt.",
        total_tokens=10,
        chunks_retrieved=1,
        chunks_used=1,
    )

    with patch(
        "services.knowledge.script_rag.index_articles_best_effort",
        return_value=1,
    ):
        result = ScriptRagService(context_builder=context_builder).enrich_article(
            episode, article
        )

    filters = context_builder.build.call_args.kwargs["filters"]
    assert filters.source_id == str(article.id)
    assert filters.source_type == "article"
    assert filters.language == article.language
    assert result.context_text == "Article-specific excerpt."
