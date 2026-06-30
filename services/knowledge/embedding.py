"""Embedding generation service."""

import logging

from apps.knowledge.models import EmbeddingStatus, KnowledgeChunk
from domain.knowledge.exceptions import EmbeddingError
from infrastructure.embedding.base import BaseEmbeddingProvider
from infrastructure.vector.base import BaseVectorStore
from infrastructure.vector.types import VectorRecord
from services.knowledge.embedding_factory import EmbeddingProviderFactory
from services.knowledge.settings import KnowledgeSettings
from services.knowledge.vector_store_factory import VectorStoreFactory

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates embeddings and persists them through the vector store."""

    def __init__(
        self,
        settings: KnowledgeSettings | None = None,
        embedding_provider: BaseEmbeddingProvider | None = None,
        vector_store: BaseVectorStore | None = None,
    ) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()
        self._embedding = embedding_provider or EmbeddingProviderFactory().create()
        self._vector_store = vector_store or VectorStoreFactory(self._settings).create()

    def embed_chunks(self, chunks: list[KnowledgeChunk]) -> int:
        """Generate embeddings for chunks and store vectors."""
        if not chunks:
            return 0

        generated = 0
        batch_size = self._settings.embedding_batch_size

        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            texts = [chunk.text for chunk in batch]
            vectors = self._embed_with_retry(texts)

            for chunk, vector in zip(batch, vectors, strict=True):
                chunk.embedding_status = EmbeddingStatus.PROCESSING
                chunk.save(update_fields=["embedding_status", "updated_at"])
                try:
                    self._vector_store.insert(
                        VectorRecord(
                            chunk_id=str(chunk.id),
                            document_id=str(chunk.document_id),
                            vector=vector,
                            metadata=chunk.metadata or {},
                        )
                    )
                    chunk.embedding_status = EmbeddingStatus.COMPLETED
                    chunk.save(update_fields=["embedding_status", "updated_at"])
                    generated += 1
                    logger.info(
                        "Embedding generated",
                        extra={
                            "event": "embedding_generated",
                            "chunk_id": str(chunk.id),
                            "document_id": str(chunk.document_id),
                            "model": self._embedding.model_name,
                        },
                    )
                except Exception as exc:
                    chunk.embedding_status = EmbeddingStatus.FAILED
                    chunk.save(update_fields=["embedding_status", "updated_at"])
                    logger.error(
                        "Embedding generation failed",
                        extra={
                            "event": "embedding_error",
                            "chunk_id": str(chunk.id),
                            "error": str(exc),
                        },
                    )

        return generated

    def retry_failed(self, document_id: str) -> int:
        """Retry embedding generation for failed chunks of a document."""
        failed = list(
            KnowledgeChunk.objects.filter(
                document_id=document_id,
                embedding_status=EmbeddingStatus.FAILED,
            ).order_by("sequence")
        )
        if not failed:
            return 0
        return self.embed_chunks(failed)

    def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        last_error: Exception | None = None
        retries = self._settings.embedding_retry_count

        for attempt in range(1, retries + 1):
            try:
                return self._embedding.embed_batch(texts)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Embedding batch failed, retrying",
                    extra={
                        "event": "embedding_retry",
                        "attempt": attempt,
                        "batch_size": len(texts),
                        "error": str(exc),
                    },
                )

        raise EmbeddingError(
            f"Embedding batch failed after {retries} attempts: {last_error}"
        )
