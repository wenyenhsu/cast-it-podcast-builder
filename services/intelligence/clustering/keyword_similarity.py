"""Keyword similarity clustering implementation."""

import re

from domain.intelligence.dtos import TopicCluster
from services.intelligence.clustering.base import (
    ClusterArticleInput,
    ClusteringStrategy,
)


class KeywordSimilarityClustering(ClusteringStrategy):
    """Cluster articles by overlapping normalized keywords."""

    def __init__(self, similarity_threshold: float = 0.3) -> None:
        self._threshold = similarity_threshold

    def cluster(self, articles: list[ClusterArticleInput]) -> list[TopicCluster]:
        if not articles:
            return []

        clusters: list[TopicCluster] = []

        for article in articles:
            article_keywords = self._normalize_keywords(article.keywords)
            matched_cluster_id = self._find_matching_cluster(
                article_keywords,
                clusters,
            )

            if matched_cluster_id is None:
                cluster_id = f"cluster-{len(clusters) + 1}"
                label = self._build_label(article)
                clusters.append(
                    TopicCluster(
                        cluster_id=cluster_id,
                        label=label,
                        article_ids=[article.article_id],
                        keywords=article.keywords[:5],
                    )
                )
                continue

            clusters = self._append_to_cluster(clusters, matched_cluster_id, article)

        return clusters

    def _find_matching_cluster(
        self,
        article_keywords: set[str],
        clusters: list[TopicCluster],
    ) -> str | None:
        if not article_keywords:
            return None

        for cluster in clusters:
            cluster_keywords = self._normalize_keywords(cluster.keywords)
            if not cluster_keywords:
                continue
            overlap = len(article_keywords & cluster_keywords)
            similarity = overlap / min(len(article_keywords), len(cluster_keywords))
            if similarity >= self._threshold:
                return cluster.cluster_id
        return None

    @staticmethod
    def _normalize_keywords(keywords: list[str]) -> set[str]:
        normalized: set[str] = set()
        for keyword in keywords:
            cleaned = re.sub(r"[^a-z0-9]+", " ", keyword.lower()).strip()
            if cleaned:
                normalized.add(cleaned)
        return normalized

    @staticmethod
    def _build_label(article: ClusterArticleInput) -> str:
        if article.keywords:
            return article.keywords[0]
        return article.title.split(":")[0][:60]

    @staticmethod
    def _append_to_cluster(
        clusters: list[TopicCluster],
        cluster_id: str,
        article: ClusterArticleInput,
    ) -> list[TopicCluster]:
        updated: list[TopicCluster] = []
        for cluster in clusters:
            if cluster.cluster_id != cluster_id:
                updated.append(cluster)
                continue
            merged_keywords = list(
                dict.fromkeys([*cluster.keywords, *article.keywords])
            )
            updated.append(
                TopicCluster(
                    cluster_id=cluster.cluster_id,
                    label=cluster.label,
                    article_ids=[*cluster.article_ids, article.article_id],
                    keywords=merged_keywords[:10],
                )
            )
        return updated
