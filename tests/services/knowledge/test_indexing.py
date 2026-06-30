"""Tests for incremental indexing service."""

from unittest.mock import MagicMock

import pytest

from apps.knowledge.models import KnowledgeDocument, SourceType
from domain.knowledge.dtos import ChunkDraft, DocumentIndexRequest
from services.knowledge.indexing import IndexingService


@pytest.fixture
def index_request() -> DocumentIndexRequest:
    return DocumentIndexRequest(
        source_type=SourceType.ARTICLE,
        source_id="article-index-1",
        title="Indexed Article",
        language="en",
        content="First paragraph.\n\nSecond paragraph for indexing.",
        metadata={"category": "technology", "tags": ["ai"]},
    )


@pytest.mark.django_db
def test_index_document_creates_chunks_and_embeddings(
    knowledge_settings,
    fake_embedding,
    fake_vector_store,
    index_request,
) -> None:
    chunking = MagicMock()
    chunking.chunk_document.return_value = [
        ChunkDraft(sequence=1, text="First paragraph.", token_count=3, metadata={}),
        ChunkDraft(
            sequence=2,
            text="Second paragraph for indexing.",
            token_count=4,
            metadata={},
        ),
    ]
    embedding = MagicMock()
    embedding.embed_chunks.side_effect = lambda chunks: len(chunks)

    service = IndexingService(
        knowledge_settings,
        chunking_service=chunking,
        embedding_service=embedding,
    )
    result = service.index_document(index_request)

    assert result.skipped is False
    assert result.chunks_created == 2
    assert result.embeddings_generated == 2
    assert KnowledgeDocument.objects.filter(source_id="article-index-1").exists()


@pytest.mark.django_db
def test_index_document_skips_unchanged_checksum(
    knowledge_settings,
    index_request,
) -> None:
    from services.knowledge.indexing import _compute_checksum

    KnowledgeDocument.objects.create(
        source_type=index_request.source_type,
        source_id=index_request.source_id,
        title=index_request.title,
        language=index_request.language,
        content=index_request.content,
        checksum=_compute_checksum(index_request.content),
        metadata=index_request.metadata,
    )

    service = IndexingService(knowledge_settings)
    result = service.index_document(index_request)

    assert result.skipped is True
    assert result.chunks_created == 0


@pytest.mark.django_db
def test_index_document_reindexes_on_content_change(
    knowledge_settings,
    index_request,
) -> None:
    from services.knowledge.indexing import _compute_checksum

    KnowledgeDocument.objects.create(
        source_type=index_request.source_type,
        source_id=index_request.source_id,
        title=index_request.title,
        language=index_request.language,
        content="Old content",
        checksum=_compute_checksum("Old content"),
        metadata=index_request.metadata,
    )

    chunking = MagicMock()
    chunking.chunk_document.return_value = [
        ChunkDraft(sequence=1, text="Updated chunk", token_count=3, metadata={}),
    ]
    embedding = MagicMock()
    embedding.embed_chunks.return_value = 1

    service = IndexingService(
        knowledge_settings,
        chunking_service=chunking,
        embedding_service=embedding,
    )
    result = service.index_document(index_request)

    assert result.reindexed is True
    assert result.chunks_created == 1
    document = KnowledgeDocument.objects.get(source_id=index_request.source_id)
    assert "Second paragraph" in document.content
