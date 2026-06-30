"""Tests for document normalizer."""

import pytest

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.knowledge.models import SourceType
from apps.providers.models import NewsSource
from services.knowledge.normalizer import DocumentNormalizer


@pytest.mark.django_db
def test_from_article(news_source: NewsSource) -> None:
    article = Article.objects.create(
        title="AI Breakthrough",
        source=news_source,
        url="https://example.com/ai",
        content_hash="hash-normalizer",
        content="Full article body.",
        summary="Short summary.",
        category="technology",
        status=ArticleStatus.PROCESSED,
    )
    request = DocumentNormalizer().from_article(article)

    assert request.source_type == SourceType.ARTICLE
    assert request.source_id == str(article.id)
    assert "AI Breakthrough" in request.content
    assert request.metadata["category"] == "technology"


@pytest.mark.django_db
def test_from_episode() -> None:
    episode = Episode.objects.create(
        title="Weekly Roundup",
        summary="Episode summary",
        description="Episode description",
        status=EpisodeStatus.COMPLETED,
    )
    request = DocumentNormalizer().from_episode(episode)

    assert request.source_type == SourceType.EPISODE
    assert request.metadata["episode_id"] == str(episode.id)
