"""Tests for embedding service."""

import pytest

from apps.knowledge.models import (
    EmbeddingStatus,
    KnowledgeChunk,
    KnowledgeDocument,
    SourceType,
)
from services.knowledge.embedding import EmbeddingService


@pytest.mark.django_db
def test_embed_chunks_updates_status(
    knowledge_settings,
    fake_embedding,
    fake_vector_store,
) -> None:
    document = KnowledgeDocument.objects.create(
        source_type=SourceType.ARTICLE,
        source_id="article-1",
        title="Test",
        language="en",
        content="Sample content",
        checksum="abc",
    )
    chunk = KnowledgeChunk.objects.create(
        document=document,
        sequence=1,
        text="Sample chunk text",
        token_count=4,
        embedding_status=EmbeddingStatus.PENDING,
    )

    service = EmbeddingService(
        knowledge_settings,
        embedding_provider=fake_embedding,
        vector_store=fake_vector_store,
    )
    generated = service.embed_chunks([chunk])

    chunk.refresh_from_db()
    assert generated == 1
    assert chunk.embedding_status == EmbeddingStatus.COMPLETED
    assert str(chunk.id) in fake_vector_store.records


@pytest.mark.django_db
def test_retry_failed_embeddings(
    knowledge_settings,
    fake_embedding,
    fake_vector_store,
) -> None:
    document = KnowledgeDocument.objects.create(
        source_type=SourceType.ARTICLE,
        source_id="article-2",
        title="Retry Test",
        language="en",
        content="Sample content",
        checksum="def",
    )
    chunk = KnowledgeChunk.objects.create(
        document=document,
        sequence=1,
        text="Failed chunk",
        token_count=2,
        embedding_status=EmbeddingStatus.FAILED,
    )

    service = EmbeddingService(
        knowledge_settings,
        embedding_provider=fake_embedding,
        vector_store=fake_vector_store,
    )
    retried = service.retry_failed(str(document.id))

    chunk.refresh_from_db()
    assert retried == 1
    assert chunk.embedding_status == EmbeddingStatus.COMPLETED
