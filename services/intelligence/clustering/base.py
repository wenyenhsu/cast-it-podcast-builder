"""Clustering strategy abstractions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from domain.intelligence.dtos import TopicCluster


@dataclass(frozen=True)
class ClusterArticleInput:
    """Minimal article data required for topic clustering."""

    article_id: UUID
    title: str
    keywords: list[str]


class ClusteringStrategy(ABC):
    """Abstract clustering strategy for grouping related articles."""

    @abstractmethod
    def cluster(self, articles: list[ClusterArticleInput]) -> list[TopicCluster]:
        """Group articles into topic clusters."""
