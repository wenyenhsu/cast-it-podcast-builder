"""Normalized article representation for news ingestion."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ArticleDTO:
    """Normalized article data returned by all news providers."""

    title: str
    source: str
    url: str
    author: str = ""
    published_at: datetime | None = None
    language: str = "en"
    category: str = ""
    summary: str = ""
    content: str = ""
    tags: list[str] = field(default_factory=list)
