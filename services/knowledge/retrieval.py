"""Semantic retrieval service."""

import logging
import time

from domain.knowledge.dtos import RetrievalFilter, RetrievalResult, RetrievedChunk
from domain.knowledge.exceptions import RetrievalError
from infrastructure.embedding.base import BaseEmbeddingProvider
from infrastructure.vector.base import BaseVectorStore
from infrastructure.vector.types import VectorSearchQuery
from services.knowledge.embedding_factory import EmbeddingProviderFactory
from services.knowledge.settings import KnowledgeSettings
from services.knowledge.vector_store_factory import VectorStoreFactory

logger = logging.getLogger(__name__)


class RetrievalService:
    """Performs semantic search and returns normalized retrieval DTOs."""

    def __init__(
        self,
        settings: KnowledgeSettings | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()
        self._embedding = embedding_provider or EmbeddingProviderFactory().create()
        self._vector_store = vector_store or VectorStoreFactory(self._settings).create()

    def retrieve(
        self,
        query: str,
        *,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
        filters: RetrievalFilter | None = None,
    ) -> RetrievalResult:
        """Retrieve the most relevant knowledge chunks for a query."""
        normalized_query = query.strip()
        if not normalized_query:
            raise RetrievalError("Retrieval query must not be empty.")

        started = time.perf_counter()
        vector_started = time.perf_counter()

        try:
            query_vector = self._embedding.embed(normalized_query)
            search_results = self._vector_store.search(
                VectorSearchQuery(
                    vector=query_vector,
                    top_k=top_k or self._settings.top_k,
                    similarity_threshold=(
                        similarity_threshold
                        if similarity_threshold is not None
                        else self._settings.similarity_threshold
                    ),
                    filters=filters,
                )
            )
        except Exception as exc:
            raise RetrievalError(f"Retrieval failed: {exc}") from exc

        vector_duration_ms = (time.perf_counter() - vector_started) * 1000.0
        chunks = [_normalize_result(result) for result in search_results]
        chunks = _normalize_scores(chunks)
        latency_ms = (time.perf_counter() - started) * 1000.0

        logger.info(
            "Retrieval completed",
            extra={
                "event": "retrieval_completed",
                "retrieved_chunk_count": len(chunks),
                "retrieval_latency_ms": latency_ms,
                "vector_search_duration_ms": vector_duration_ms,
            },
        )

        return RetrievalResult(
            query=normalized_query,
            chunks=chunks,
            retrieval_latency_ms=latency_ms,
            vector_search_duration_ms=vector_duration_ms,
        )


def _normalize_result(result: object) -> RetrievedChunk:
    from infrastructure.vector.types import VectorSearchResult

    if not isinstance(result, VectorSearchResult):
        raise RetrievalError("Invalid vector search result type.")

    metadata = result.metadata
    return RetrievedChunk(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        source_type=str(metadata.get("source_type", "")),
        source_id=str(metadata.get("source_id", "")),
        title=str(metadata.get("title", "")),
        text=str(metadata.get("chunk_text", "")),
        score=float(result.score),
        token_count=int(metadata.get("token_count", 0)),
        metadata=metadata,
    )


def _normalize_scores(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    if not chunks:
        return chunks

    max_score = max(chunk.score for chunk in chunks)
    min_score = min(chunk.score for chunk in chunks)
    if max_score == min_score:
        return [
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                title=chunk.title,
                text=chunk.text,
                score=1.0,
                token_count=chunk.token_count,
                metadata=chunk.metadata,
            )
            for chunk in chunks
        ]

    span = max_score - min_score
    return [
        RetrievedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            source_type=chunk.source_type,
            source_id=chunk.source_id,
            title=chunk.title,
            text=chunk.text,
            score=(chunk.score - min_score) / span,
            token_count=chunk.token_count,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]
