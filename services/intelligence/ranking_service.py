"""Article ranking service."""

import logging
import time
from uuid import UUID

from apps.articles.models import Article
from domain.intelligence.dtos import RankedArticle, TopicCluster

logger = logging.getLogger(__name__)


class ArticleRankingService:
    """Ranks articles by importance score and freshness."""

    def rank(
        self,
        articles: list[Article],
        clusters: list[TopicCluster] | None = None,
    ) -> list[RankedArticle]:
        """Return articles ordered by descending importance."""
        started = time.perf_counter()
        cluster_map = self._build_cluster_map(clusters or [])

        sorted_articles = sorted(
            articles,
            key=lambda article: (
                article.importance_score or 0,
                article.published_at.timestamp() if article.published_at else 0,
            ),
            reverse=True,
        )

        ranked = [
            RankedArticle(
                article_id=article.id,
                rank=index + 1,
                score=article.importance_score or 0,
                cluster_id=cluster_map.get(article.id, ""),
            )
            for index, article in enumerate(sorted_articles)
        ]

        elapsed = time.perf_counter() - started
        logger.info(
            "Ranking completed",
            extra={
                "event": "ranking_completed",
                "article_count": len(ranked),
                "elapsed_time": elapsed,
            },
        )
        return ranked

    @staticmethod
    def _build_cluster_map(clusters: list[TopicCluster]) -> dict[UUID, str]:
        mapping: dict[UUID, str] = {}
        for cluster in clusters:
            for article_id in cluster.article_ids:
                mapping[article_id] = cluster.cluster_id
        return mapping
