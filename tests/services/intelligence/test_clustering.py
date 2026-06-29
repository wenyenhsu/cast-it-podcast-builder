"""Tests for keyword similarity clustering."""

from uuid import uuid4

from services.intelligence.clustering.base import ClusterArticleInput
from services.intelligence.clustering.keyword_similarity import (
    KeywordSimilarityClustering,
)


class TestKeywordSimilarityClustering:
    def test_groups_articles_with_shared_keywords(self) -> None:
        clustering = KeywordSimilarityClustering(similarity_threshold=0.3)
        first_id = uuid4()
        second_id = uuid4()
        third_id = uuid4()

        clusters = clustering.cluster(
            [
                ClusterArticleInput(
                    first_id,
                    "GPT-5 Launch",
                    ["OpenAI", "GPT-5", "LLM"],
                ),
                ClusterArticleInput(
                    second_id,
                    "GPT-5 API Released",
                    ["OpenAI", "GPT-5", "API"],
                ),
                ClusterArticleInput(
                    third_id,
                    "Kubernetes 2.0",
                    ["Kubernetes", "Cloud", "DevOps"],
                ),
            ]
        )

        assert len(clusters) == 2
        gpt_cluster = next(
            cluster for cluster in clusters if first_id in cluster.article_ids
        )
        assert second_id in gpt_cluster.article_ids
        assert third_id not in gpt_cluster.article_ids

    def test_empty_input_returns_empty_clusters(self) -> None:
        clustering = KeywordSimilarityClustering()
        assert clustering.cluster([]) == []
