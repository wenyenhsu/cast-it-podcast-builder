"""Knowledge domain data transfer objects."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ChunkDraft:
    """A chunk produced by the chunking service before persistence."""

    sequence: int
    text: str
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentIndexRequest:
    """Payload for indexing a normalized knowledge document."""

    source_type: str
    source_id: str
    title: str
    language: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class IndexResult:
    """Result of an indexing operation."""

    document_id: str
    chunks_created: int
    embeddings_generated: int
    skipped: bool = False
    reindexed: bool = False


@dataclass(frozen=True)
class RetrievalFilter:
    """Metadata filters applied during semantic search."""

    language: str | None = None
    source_type: str | None = None
    category: str | None = None
    publish_date_from: date | None = None
    publish_date_to: date | None = None
    episode_id: str | None = None
    tags: list[str] | None = None


@dataclass(frozen=True)
class RetrievedChunk:
    """Normalized chunk returned from retrieval."""

    chunk_id: str
    document_id: str
    source_type: str
    source_id: str
    title: str
    text: str
    score: float
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    """Result of a semantic retrieval query."""

    query: str
    chunks: list[RetrievedChunk]
    retrieval_latency_ms: float
    vector_search_duration_ms: float


@dataclass(frozen=True)
class ContextBlock:
    """One ranked context block for LLM prompting."""

    chunk_id: str
    title: str
    text: str
    score: float
    token_count: int
    source_type: str
    source_id: str


@dataclass(frozen=True)
class AssembledContext:
    """Final assembled context ready for LLM consumption."""

    query: str
    blocks: list[ContextBlock]
    context_text: str
    total_tokens: int
    chunks_retrieved: int
    chunks_used: int
