"""Tests for episode planning pipeline."""

from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode
from services.intelligence.classification_service import ArticleClassificationService
from services.intelligence.keyword_service import KeywordExtractionService
from services.intelligence.pipeline import EpisodePlanningPipeline
from services.intelligence.scoring_service import ArticleScoreService
from services.intelligence.summary_service import ArticleSummaryService


@pytest.mark.django_db
class TestEpisodePlanningPipeline:
    def test_run_processes_articles_and_creates_episode(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        news_source: object,
    ) -> None:
        today = timezone.now()
        for index in range(3):
            Article.objects.create(
                source=news_source,  # type: ignore[arg-type]
                title=f"Story {index}",
                url=f"https://example.com/story-{index}",
                content=f"Content for story {index}",
                content_hash=f"hash-{index}",
                published_at=today,
                status=ArticleStatus.COLLECTED,
            )

        pipeline = EpisodePlanningPipeline(
            mock_llm,
            summary_service=ArticleSummaryService(
                mock_llm,
                prompt_builder=prompt_builder,  # type: ignore[arg-type]
            ),
            classification_service=ArticleClassificationService(
                mock_llm,
                prompt_builder=prompt_builder,  # type: ignore[arg-type]
            ),
            keyword_service=KeywordExtractionService(
                mock_llm,
                prompt_builder=prompt_builder,  # type: ignore[arg-type]
            ),
            scoring_service=ArticleScoreService(
                mock_llm,
                prompt_builder=prompt_builder,  # type: ignore[arg-type]
            ),
        )

        result = pipeline.run()

        assert result.articles_processed == 3
        assert result.clusters_created >= 1
        assert result.episode_plan is not None
        assert Episode.objects.count() == 1

    def test_run_with_no_articles_returns_empty_result(
        self,
        mock_llm: MagicMock,
    ) -> None:
        pipeline = EpisodePlanningPipeline(mock_llm)
        result = pipeline.run()

        assert result.articles_processed == 0
        assert result.episode_plan is None
