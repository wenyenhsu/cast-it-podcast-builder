"""Tests for retrieval service."""

from domain.knowledge.dtos import RetrievalFilter
from infrastructure.vector.types import VectorRecord
from services.knowledge.retrieval import RetrievalService


def test_retrieve_returns_normalized_chunks(
    knowledge_settings,
    fake_embedding,
    fake_vector_store,
) -> None:
    query_vector = fake_embedding.embed("machine learning podcast")
    fake_vector_store.insert(
        VectorRecord(
            chunk_id="chunk-1",
            document_id="doc-1",
            vector=query_vector,
            metadata={
                "source_type": "article",
                "source_id": "a-1",
                "title": "AI News",
                "chunk_text": "Machine learning advances in 2026.",
                "token_count": 6,
            },
        )
    )

    service = RetrievalService(
        knowledge_settings,
        embedding_provider=fake_embedding,
        vector_store=fake_vector_store,
    )
    result = service.retrieve("machine learning podcast")

    assert len(result.chunks) == 1
    assert result.chunks[0].title == "AI News"
    assert result.chunks[0].score == 1.0
    assert result.retrieval_latency_ms >= 0


def test_retrieve_applies_source_filter(
    knowledge_settings,
    fake_embedding,
    fake_vector_store,
) -> None:
    vector = fake_embedding.embed("filter test")
    fake_vector_store.insert(
        VectorRecord(
            chunk_id="chunk-1",
            document_id="doc-1",
            vector=vector,
            metadata={
                "source_type": "article",
                "source_id": "a-1",
                "title": "Article",
                "chunk_text": "Article text",
                "token_count": 2,
            },
        )
    )
    fake_vector_store.insert(
        VectorRecord(
            chunk_id="chunk-2",
            document_id="doc-2",
            vector=vector,
            metadata={
                "source_type": "episode",
                "source_id": "e-1",
                "title": "Episode",
                "chunk_text": "Episode text",
                "token_count": 2,
            },
        )
    )

    service = RetrievalService(
        knowledge_settings,
        embedding_provider=fake_embedding,
        vector_store=fake_vector_store,
    )
    result = service.retrieve(
        "filter test",
        filters=RetrievalFilter(source_type="article"),
    )

    assert len(result.chunks) == 1
    assert result.chunks[0].source_type == "article"
