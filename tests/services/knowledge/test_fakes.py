"""Tests for fake vector store and embedding provider."""

from domain.knowledge.dtos import RetrievalFilter
from infrastructure.vector.types import VectorRecord, VectorSearchQuery
from tests.services.knowledge.fakes import FakeEmbeddingProvider, FakeVectorStore


def test_fake_vector_store_search_respects_top_k() -> None:
    embedding = FakeEmbeddingProvider(dimensions=4)
    store = FakeVectorStore()
    vector = embedding.embed("query")

    for index in range(3):
        store.insert(
            VectorRecord(
                chunk_id=f"chunk-{index}",
                document_id=f"doc-{index}",
                vector=vector,
                metadata={"source_type": "article", "chunk_text": f"text {index}"},
            )
        )

    results = store.search(
        VectorSearchQuery(
            vector=vector,
            top_k=2,
            similarity_threshold=0.0,
        )
    )
    assert len(results) == 2


def test_fake_vector_store_filter_by_source_type() -> None:
    embedding = FakeEmbeddingProvider(dimensions=4)
    store = FakeVectorStore()
    vector = embedding.embed("query")

    store.insert(
        VectorRecord(
            chunk_id="a",
            document_id="d1",
            vector=vector,
            metadata={"source_type": "article"},
        )
    )
    store.insert(
        VectorRecord(
            chunk_id="e",
            document_id="d2",
            vector=vector,
            metadata={"source_type": "episode"},
        )
    )

    results = store.search(
        VectorSearchQuery(
            vector=vector,
            top_k=5,
            similarity_threshold=0.0,
            filters=RetrievalFilter(source_type="episode"),
        )
    )
    assert len(results) == 1
    assert results[0].chunk_id == "e"
