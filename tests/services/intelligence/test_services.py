"""Tests for article intelligence services."""

from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus, Tag
from domain.intelligence.dtos import TopicCluster
from services.intelligence.classification_service import ArticleClassificationService
from services.intelligence.episode_planner_service import EpisodePlannerService
from services.intelligence.keyword_service import KeywordExtractionService
from services.intelligence.ranking_service import ArticleRankingService
from services.intelligence.scoring_service import ArticleScoreService
from services.intelligence.summary_service import ArticleSummaryService


@pytest.mark.django_db
class TestArticleSummaryService:
    def test_summarize_persists_summary(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        sample_article: Article,
    ) -> None:
        service = ArticleSummaryService(mock_llm, prompt_builder=prompt_builder)  # type: ignore[arg-type]
        result = service.summarize(sample_article)

        assert result is not None
        sample_article.refresh_from_db()
        assert sample_article.summary.startswith("This is a generated summary")
        assert sample_article.summary_generated_at is not None
        assert sample_article.status == ArticleStatus.PROCESSED

    def test_summarize_skips_already_summarized(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        sample_article: Article,
    ) -> None:
        sample_article.summary = "Existing summary"
        sample_article.summary_generated_at = timezone.now()
        sample_article.save()

        service = ArticleSummaryService(mock_llm, prompt_builder=prompt_builder)  # type: ignore[arg-type]
        service.summarize(sample_article)

        mock_llm.chat.assert_not_called()


@pytest.mark.django_db
class TestArticleClassificationService:
    def test_classify_persists_category(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        sample_article: Article,
    ) -> None:
        sample_article.summary = "Summary text"
        sample_article.save()

        service = ArticleClassificationService(mock_llm, prompt_builder=prompt_builder)  # type: ignore[arg-type]
        result = service.classify(sample_article)

        assert result.category == "AI"
        sample_article.refresh_from_db()
        assert sample_article.category == "AI"
        assert sample_article.classified_at is not None


@pytest.mark.django_db
class TestKeywordExtractionService:
    def test_extract_persists_keywords(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        sample_article: Article,
    ) -> None:
        sample_article.summary = "Summary"
        sample_article.category = "AI"
        sample_article.save()

        service = KeywordExtractionService(mock_llm, prompt_builder=prompt_builder)  # type: ignore[arg-type]
        result = service.extract(sample_article)

        assert len(result.keywords) >= 1
        sample_article.refresh_from_db()
        assert sample_article.keywords_generated_at is not None
        assert Tag.objects.filter(article_tags__article=sample_article).exists()


@pytest.mark.django_db
class TestArticleScoreService:
    def test_score_persists_importance_score(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        sample_article: Article,
    ) -> None:
        sample_article.summary = "Summary"
        sample_article.category = "AI"
        sample_article.save()

        service = ArticleScoreService(mock_llm, prompt_builder=prompt_builder)  # type: ignore[arg-type]
        result = service.score(sample_article)

        assert 0 <= result.score <= 100
        sample_article.refresh_from_db()
        assert sample_article.importance_score == result.score


@pytest.mark.django_db
class TestArticleRankingService:
    def test_rank_orders_by_score(
        self,
        news_source: object,
    ) -> None:
        first = Article.objects.create(
            source=news_source,  # type: ignore[arg-type]
            title="Low",
            url="https://example.com/low",
            content_hash="low",
            importance_score=40,
            published_at=timezone.now(),
        )
        second = Article.objects.create(
            source=news_source,  # type: ignore[arg-type]
            title="High",
            url="https://example.com/high",
            content_hash="high",
            importance_score=90,
            published_at=timezone.now(),
        )

        ranked = ArticleRankingService().rank([first, second])

        assert ranked[0].article_id == second.id
        assert ranked[0].rank == 1


@pytest.mark.django_db
class TestEpisodePlannerService:
    def test_plan_episode_creates_episode_and_mappings(
        self,
        mock_llm: MagicMock,
        prompt_builder: object,
        sample_article: Article,
    ) -> None:
        sample_article.summary = "Summary"
        sample_article.category = "AI"
        sample_article.importance_score = 90
        sample_article.save()

        ranked = ArticleRankingService().rank([sample_article])
        clusters = [
            TopicCluster(
                cluster_id="cluster-1",
                label="OpenAI",
                article_ids=[sample_article.id],
                keywords=["OpenAI"],
            )
        ]

        service = EpisodePlannerService(mock_llm, prompt_builder=prompt_builder)  # type: ignore[arg-type]
        plan = service.plan_episode(ranked, [sample_article], clusters)

        assert plan.title == "AI Breakthroughs Today"
        assert sample_article.id in plan.article_ids
        sample_article.refresh_from_db()
        assert sample_article.status == ArticleStatus.SELECTED
