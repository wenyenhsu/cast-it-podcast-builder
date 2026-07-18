"""PostgreSQL pgvector vector store adapter."""

import logging
import uuid
from typing import Any

from django.db import connection
from pgvector.django import CosineDistance

from apps.knowledge.models import EmbeddingStatus, KnowledgeChunk, KnowledgeDocument
from domain.knowledge.exceptions import VectorStoreError
from infrastructure.vector.base import BaseVectorStore
from infrastructure.vector.types import (
    VectorRecord,
    VectorSearchQuery,
    VectorSearchResult,
)

logger = logging.getLogger(__name__)


class PgVectorStore(BaseVectorStore):
    """Vector store backed by PostgreSQL pgvector extension."""

    def insert(self, record: VectorRecord) -> str:
        try:
            chunk = KnowledgeChunk.objects.get(pk=record.chunk_id)
            chunk.embedding = record.vector
            chunk.save(update_fields=["embedding", "updated_at"])
            return str(chunk.id)
        except KnowledgeChunk.DoesNotExist as exc:
            raise VectorStoreError(
                f"Chunk {record.chunk_id} not found for vector insert."
            ) from exc
        except Exception as exc:
            raise VectorStoreError(f"Vector insert failed: {exc}") from exc

    def update(self, record: VectorRecord) -> None:
        self.insert(record)

    def delete(self, chunk_id: str) -> None:
        try:
            KnowledgeChunk.objects.filter(pk=chunk_id).update(
                embedding=None,
                embedding_status=EmbeddingStatus.PENDING,
            )
        except Exception as exc:
            raise VectorStoreError(f"Vector delete failed: {exc}") from exc

    def delete_by_document(self, document_id: str) -> None:
        try:
            KnowledgeChunk.objects.filter(
                document_id=uuid.UUID(document_id),
            ).update(
                embedding=None,
                embedding_status=EmbeddingStatus.PENDING,
            )
        except Exception as exc:
            raise VectorStoreError(f"Vector delete by document failed: {exc}") from exc

    def search(self, query: VectorSearchQuery) -> list[VectorSearchResult]:
        started = _perf_counter_ms()
        try:
            qs = KnowledgeChunk.objects.filter(
                embedding__isnull=False,
                embedding_status=EmbeddingStatus.COMPLETED,
            ).select_related("document")

            qs = _apply_filters(qs, query.filters)

            annotated = qs.annotate(
                distance=CosineDistance("embedding", query.vector),
            ).order_by("distance")

            results: list[VectorSearchResult] = []
            for chunk in annotated[: query.top_k * 2]:
                similarity = 1.0 - float(chunk.distance)
                if similarity < query.similarity_threshold:
                    continue
                metadata = _build_result_metadata(chunk)
                results.append(
                    VectorSearchResult(
                        chunk_id=str(chunk.id),
                        document_id=str(chunk.document_id),
                        score=similarity,
                        metadata=metadata,
                    )
                )
                if len(results) >= query.top_k:
                    break

            duration_ms = _perf_counter_ms() - started
            logger.info(
                "Vector search completed",
                extra={
                    "event": "vector_search_completed",
                    "result_count": len(results),
                    "vector_search_duration_ms": duration_ms,
                    "top_k": query.top_k,
                },
            )
            return results
        except Exception as exc:
            raise VectorStoreError(f"Vector search failed: {exc}") from exc

    def health_check(self) -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                row = cursor.fetchone()
                return row is not None
        except Exception as exc:
            logger.warning(
                "Vector store health check failed",
                extra={"event": "vector_store_health_failed", "error": str(exc)},
            )
            return False

    def count(self) -> int:
        return KnowledgeChunk.objects.filter(
            embedding__isnull=False,
            embedding_status=EmbeddingStatus.COMPLETED,
        ).count()


def _apply_filters(
    qs: Any,
    filters: Any | None,
) -> Any:
    if filters is None:
        return qs

    if filters.language:
        qs = qs.filter(document__language=filters.language)
    if filters.source_type:
        qs = qs.filter(document__source_type=filters.source_type)
    if filters.source_id:
        qs = qs.filter(document__source_id=filters.source_id)
    if filters.category:
        qs = qs.filter(document__metadata__category=filters.category)
    if filters.episode_id:
        qs = qs.filter(document__metadata__episode_id=filters.episode_id)
    if filters.tags:
        qs = qs.filter(document__metadata__tags__contains=filters.tags)
    if filters.publish_date_from:
        qs = qs.filter(
            document__metadata__publish_date__gte=filters.publish_date_from.isoformat()
        )
    if filters.publish_date_to:
        qs = qs.filter(
            document__metadata__publish_date__lte=filters.publish_date_to.isoformat()
        )
    return qs


def _build_result_metadata(chunk: KnowledgeChunk) -> dict[str, Any]:
    document: KnowledgeDocument = chunk.document
    metadata = dict(document.metadata or {})
    metadata.update(
        {
            "chunk_sequence": chunk.sequence,
            "chunk_text": chunk.text,
            "token_count": chunk.token_count,
            "title": document.title,
            "source_type": document.source_type,
            "source_id": document.source_id,
            "language": document.language,
        }
    )
    chunk_meta = chunk.metadata or {}
    metadata.update(chunk_meta)
    return metadata


def _perf_counter_ms() -> float:
    import time

    return time.perf_counter() * 1000.0
