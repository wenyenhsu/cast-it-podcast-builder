"""Keyword similarity clustering implementation."""

import re

from domain.intelligence.dtos import TopicCluster
from services.intelligence.clustering.base import (
    ClusterArticleInput,
    ClusteringStrategy,
)

# Words too common in headlines to signal "same story".
_STOPWORDS = frozenset(
    """a an and are as at be but by for from has have how in is it its new of on
    or that the this to was were will with you your""".split()
)


class KeywordSimilarityClustering(ClusteringStrategy):
    """Cluster articles that cover the same story.

    Similarity is Jaccard overlap over the union of title words and
    keywords. Tags alone are too coarse — most tech stories share a tag
    like "LLM", which previously collapsed unrelated articles into one
    cluster; title words separate distinct stories while same-story
    coverage across sources still overlaps heavily.
    """

    def __init__(self, similarity_threshold: float = 0.3) -> None:
        self._threshold = similarity_threshold
        self._cluster_signals: dict[str, set[str]] = {}

    def cluster(self, articles: list[ClusterArticleInput]) -> list[TopicCluster]:
        if not articles:
            return []

        clusters: list[TopicCluster] = []
        self._cluster_signals = {}

        for article in articles:
            article_signals = self._signals(article)
            matched_cluster_id = self._find_matching_cluster(
                article_signals,
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
                self._cluster_signals[cluster_id] = set(article_signals)
                continue

            clusters = self._append_to_cluster(clusters, matched_cluster_id, article)
            self._cluster_signals[matched_cluster_id] |= article_signals

        return clusters

    def _find_matching_cluster(
        self,
        article_signals: set[str],
        clusters: list[TopicCluster],
    ) -> str | None:
        if not article_signals:
            return None

        for cluster in clusters:
            cluster_signals = self._cluster_signals.get(cluster.cluster_id, set())
            if not cluster_signals:
                continue
            overlap = len(article_signals & cluster_signals)
            union = len(article_signals | cluster_signals)
            if union and (overlap / union) >= self._threshold:
                return cluster.cluster_id
        return None

    @classmethod
    def _signals(cls, article: ClusterArticleInput) -> set[str]:
        """Title words plus keywords, normalized, minus stopwords."""
        tokens = cls._normalize_keywords(article.keywords)
        for word in re.split(r"[^a-z0-9]+", article.title.lower()):
            if word and word not in _STOPWORDS:
                tokens.add(word)
        return tokens

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
