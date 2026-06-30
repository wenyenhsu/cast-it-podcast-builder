"""Vector store record and query types."""

from dataclasses import dataclass, field
from typing import Any

from domain.knowledge.dtos import RetrievalFilter


@dataclass(frozen=True)
class VectorRecord:
    """A vector record stored in the vector database."""

    chunk_id: str
    document_id: str
    vector: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchResult:
    """One result from a vector similarity search."""

    chunk_id: str
    document_id: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VectorSearchQuery:
    """Query parameters for vector similarity search."""

    vector: list[float]
    top_k: int
    similarity_threshold: float
    filters: RetrievalFilter | None = None
