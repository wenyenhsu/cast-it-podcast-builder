"""Content intelligence data transfer objects."""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class SummaryDTO:
    """Result of summarizing an article."""

    article_id: UUID
    summary: str
    generated_at: datetime


@dataclass(frozen=True)
class ClassificationDTO:
    """Result of classifying an article."""

    article_id: UUID
    category: str
    classified_at: datetime


@dataclass(frozen=True)
class KeywordDTO:
    """Extracted keywords for an article."""

    article_id: UUID
    keywords: list[str]
    extracted_at: datetime


@dataclass(frozen=True)
class ScoreDTO:
    """Importance score breakdown for an article."""

    article_id: UUID
    score: int
    freshness_score: float
    source_score: float
    category_score: float
    keyword_score: float
    llm_score: float
    scored_at: datetime


@dataclass(frozen=True)
class TopicCluster:
    """A group of related articles sharing a common topic."""

    cluster_id: str
    label: str
    article_ids: list[UUID] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RankedArticle:
    """An article with ranking metadata."""

    article_id: UUID
    rank: int
    score: int
    cluster_id: str = ""


@dataclass(frozen=True)
class EpisodePlanDTO:
    """Planned episode with selected articles and generated metadata."""

    episode_id: UUID
    title: str
    summary: str
    article_ids: list[UUID]
    estimated_duration_seconds: int
    language: str = "en"
