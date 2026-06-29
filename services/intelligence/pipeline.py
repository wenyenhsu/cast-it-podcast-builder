"""Episode planning pipeline orchestration."""

import logging
import time
from dataclasses import dataclass, field
from datetime import timedelta
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from domain.intelligence.dtos import EpisodePlanDTO
from services.intelligence.classification_service import ArticleClassificationService
from services.intelligence.episode_planner_service import EpisodePlannerService
from services.intelligence.keyword_service import KeywordExtractionService
from services.intelligence.ranking_service import ArticleRankingService
from services.intelligence.scoring_service import ArticleScoreService
from services.intelligence.summary_service import ArticleSummaryService
from services.intelligence.topic_cluster_service import TopicClusteringService

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Summary of a completed episode planning pipeline run."""

    articles_processed: int = 0
    clusters_created: int = 0
    episode_plan: EpisodePlanDTO | None = None
    elapsed_time: float = 0.0
    errors: list[str] = field(default_factory=list)


class EpisodePlanningPipeline:
    """Orchestrates content intelligence steps before script generation."""

    def __init__(
        self,
        llm_service: "LLMService",
        summary_service: ArticleSummaryService | None = None,
        classification_service: ArticleClassificationService | None = None,
        keyword_service: KeywordExtractionService | None = None,
        clustering_service: TopicClusteringService | None = None,
        scoring_service: ArticleScoreService | None = None,
        ranking_service: ArticleRankingService | None = None,
        planner_service: EpisodePlannerService | None = None,
    ) -> None:
        self._summary_service = summary_service or ArticleSummaryService(llm_service)
        self._classification_service = classification_service or (
            ArticleClassificationService(llm_service)
        )
        self._keyword_service = keyword_service or KeywordExtractionService(llm_service)
        self._clustering_service = clustering_service or TopicClusteringService()
        self._scoring_service = scoring_service or ArticleScoreService(llm_service)
        self._ranking_service = ranking_service or ArticleRankingService()
        self._planner_service = planner_service or EpisodePlannerService(llm_service)

    def run(self, *, language: str = "en") -> PipelineResult:
        """Execute the full episode planning pipeline."""
        started = time.perf_counter()
        result = PipelineResult()

        articles = list(self._load_todays_articles())
        if not articles:
            logger.info(
                "Episode planning skipped, no articles found",
                extra={"event": "pipeline_skipped"},
            )
            result.elapsed_time = time.perf_counter() - started
            return result

        for article in articles:
            try:
                self._summary_service.summarize(article)
                self._classification_service.classify(article)
                self._keyword_service.extract(article)
                self._scoring_service.score(article)
                result.articles_processed += 1
            except Exception as exc:
                message = f"Failed to process article {article.id}: {exc}"
                logger.exception(
                    "Pipeline article processing failed",
                    extra={
                        "event": "pipeline_error",
                        "article_id": str(article.id),
                    },
                )
                result.errors.append(message)

        refreshed = list(Article.objects.filter(id__in=[a.id for a in articles]))
        clusters = self._clustering_service.cluster_articles(refreshed)
        result.clusters_created = len(clusters)

        ranked = self._ranking_service.rank(refreshed, clusters)
        if ranked:
            result.episode_plan = self._planner_service.plan_episode(
                ranked,
                refreshed,
                clusters,
                language=language,
            )

        result.elapsed_time = time.perf_counter() - started
        logger.info(
            "Episode planning pipeline completed",
            extra={
                "event": "pipeline_completed",
                "articles_processed": result.articles_processed,
                "cluster_count": result.clusters_created,
                "episode_id": (
                    str(result.episode_plan.episode_id) if result.episode_plan else None
                ),
                "elapsed_time": result.elapsed_time,
            },
        )
        return result

    @staticmethod
    def _load_todays_articles() -> list[Article]:
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_start = today_start + timedelta(days=1)

        return list(
            Article.objects.filter(
                status__in=[ArticleStatus.COLLECTED, ArticleStatus.PROCESSED],
                published_at__gte=today_start,
                published_at__lt=tomorrow_start,
            )
            .select_related("source")
            .prefetch_related("tags")
            .order_by("-published_at")
        )
