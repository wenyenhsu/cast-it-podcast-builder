"""Topic clustering services."""

import logging
import time
from uuid import UUID

from apps.articles.models import Article
from domain.intelligence.dtos import TopicCluster
from services.intelligence.clustering.base import (
    ClusterArticleInput,
    ClusteringStrategy,
)
from services.intelligence.clustering.keyword_similarity import (
    KeywordSimilarityClustering,
)

logger = logging.getLogger(__name__)


class TopicClusteringService:
    """Groups articles into topic clusters using a pluggable strategy."""

    def __init__(self, strategy: ClusteringStrategy | None = None) -> None:
        self._strategy = strategy or KeywordSimilarityClustering()

    def cluster_articles(self, articles: list[Article]) -> list[TopicCluster]:
        """Cluster the given articles by topic."""
        started = time.perf_counter()
        inputs = [self._to_cluster_input(article) for article in articles]
        clusters = self._strategy.cluster(inputs)

        elapsed = time.perf_counter() - started
        logger.info(
            "Topic clustering completed",
            extra={
                "event": "clustering_completed",
                "cluster_count": len(clusters),
                "article_count": len(articles),
                "elapsed_time": elapsed,
            },
        )
        return clusters

    @staticmethod
    def _to_cluster_input(article: Article) -> ClusterArticleInput:
        keywords = list(article.tags.values_list("name", flat=True))
        return ClusterArticleInput(
            article_id=article.id,
            title=article.title,
            keywords=keywords,
        )


class TopicClusterService:
    """Utility service for querying topic cluster membership."""

    def find_cluster_for_article(
        self,
        article_id: UUID,
        clusters: list[TopicCluster],
    ) -> TopicCluster | None:
        """Return the cluster containing the given article, if any."""
        for cluster in clusters:
            if article_id in cluster.article_ids:
                return cluster
        return None

    def get_cluster_labels(self, clusters: list[TopicCluster]) -> dict[UUID, str]:
        """Map article IDs to cluster labels."""
        labels: dict[UUID, str] = {}
        for cluster in clusters:
            for article_id in cluster.article_ids:
                labels[article_id] = cluster.label
        return labels
