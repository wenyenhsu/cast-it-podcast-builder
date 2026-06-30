"""Incremental knowledge indexing service."""

import hashlib
import logging

from django.db import transaction

from apps.knowledge.models import EmbeddingStatus, KnowledgeChunk, KnowledgeDocument
from domain.knowledge.dtos import DocumentIndexRequest, IndexResult
from services.knowledge.chunking import ChunkingService
from services.knowledge.embedding import EmbeddingService
from services.knowledge.settings import KnowledgeSettings
from services.knowledge.vector_store_factory import VectorStoreFactory

logger = logging.getLogger(__name__)


class IndexingService:
    """Indexes and incrementally re-indexes knowledge documents."""

    def __init__(
        self,
        settings: KnowledgeSettings | None = None,
        chunking_service: ChunkingService | None = None,
        embedding_service: EmbeddingService | None = None,
    ) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()
        self._chunking = chunking_service or ChunkingService(self._settings)
        self._embedding = embedding_service or EmbeddingService(self._settings)
        self._vector_store = VectorStoreFactory(self._settings).create()

    def index_document(self, request: DocumentIndexRequest) -> IndexResult:
        """Index or incrementally re-index a knowledge document."""
        checksum = _compute_checksum(request.content)
        existing = KnowledgeDocument.objects.filter(
            source_type=request.source_type,
            source_id=request.source_id,
        ).first()

        if existing and existing.checksum == checksum:
            logger.info(
                "Document indexing skipped",
                extra={
                    "event": "document_index_skipped",
                    "document_id": str(existing.id),
                    "source_type": request.source_type,
                    "source_id": request.source_id,
                },
            )
            return IndexResult(
                document_id=str(existing.id),
                chunks_created=0,
                embeddings_generated=0,
                skipped=True,
            )

        if existing:
            return self._reindex(existing, request, checksum)

        return self._create_and_index(request, checksum)

    @transaction.atomic
    def _create_and_index(
        self,
        request: DocumentIndexRequest,
        checksum: str,
    ) -> IndexResult:
        document = KnowledgeDocument.objects.create(
            source_type=request.source_type,
            source_id=request.source_id,
            title=request.title,
            language=request.language,
            content=request.content,
            checksum=checksum,
            metadata=request.metadata,
        )
        chunks_created, embeddings_generated = self._index_chunks(document, request)
        logger.info(
            "Document indexed",
            extra={
                "event": "document_indexed",
                "document_id": str(document.id),
                "source_type": request.source_type,
                "source_id": request.source_id,
                "chunks_created": chunks_created,
                "embeddings_generated": embeddings_generated,
            },
        )
        return IndexResult(
            document_id=str(document.id),
            chunks_created=chunks_created,
            embeddings_generated=embeddings_generated,
            reindexed=False,
        )

    @transaction.atomic
    def _reindex(
        self,
        document: KnowledgeDocument,
        request: DocumentIndexRequest,
        checksum: str,
    ) -> IndexResult:
        self._vector_store.delete_by_document(str(document.id))
        document.chunks.all().delete()

        document.title = request.title
        document.language = request.language
        document.content = request.content
        document.checksum = checksum
        document.metadata = request.metadata
        document.save(
            update_fields=[
                "title",
                "language",
                "content",
                "checksum",
                "metadata",
                "updated_at",
            ]
        )

        chunks_created, embeddings_generated = self._index_chunks(document, request)
        logger.info(
            "Document reindexed",
            extra={
                "event": "document_reindexed",
                "document_id": str(document.id),
                "source_type": request.source_type,
                "source_id": request.source_id,
                "chunks_created": chunks_created,
                "embeddings_generated": embeddings_generated,
            },
        )
        return IndexResult(
            document_id=str(document.id),
            chunks_created=chunks_created,
            embeddings_generated=embeddings_generated,
            reindexed=True,
        )

    def _index_chunks(
        self,
        document: KnowledgeDocument,
        request: DocumentIndexRequest,
    ) -> tuple[int, int]:
        drafts = self._chunking.chunk_document(
            request.content,
            metadata={"source_type": request.source_type},
        )
        chunk_models: list[KnowledgeChunk] = []
        for draft in drafts:
            chunk_models.append(
                KnowledgeChunk.objects.create(
                    document=document,
                    sequence=draft.sequence,
                    text=draft.text,
                    token_count=draft.token_count,
                    embedding_status=EmbeddingStatus.PENDING,
                    metadata=draft.metadata,
                )
            )

        embeddings_generated = self._embedding.embed_chunks(chunk_models)
        return len(chunk_models), embeddings_generated


def _compute_checksum(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
