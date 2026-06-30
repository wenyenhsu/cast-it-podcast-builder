"""Test doubles for knowledge service tests."""

from infrastructure.embedding.base import BaseEmbeddingProvider
from infrastructure.vector.base import BaseVectorStore
from infrastructure.vector.types import (
    VectorRecord,
    VectorSearchQuery,
    VectorSearchResult,
)


class FakeEmbeddingProvider(BaseEmbeddingProvider):
    """Deterministic embedding provider for unit tests."""

    def __init__(self, dimensions: int = 8) -> None:
        self._dimensions = dimensions
        self._model = "fake-embed-model"

    @property
    def model_name(self) -> str:
        return self._model

    def embed(self, text: str) -> list[float]:
        return self._vector_for(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._vector_for(text) for text in texts]

    def health_check(self) -> bool:
        return True

    def _vector_for(self, text: str) -> list[float]:
        seed = sum(ord(char) for char in text) or 1
        return [
            ((seed * (index + 1)) % 100) / 100.0 for index in range(self._dimensions)
        ]


class FakeVectorStore(BaseVectorStore):
    """In-memory vector store for unit tests."""

    def __init__(self) -> None:
        self.records: dict[str, VectorRecord] = {}
        self.healthy = True

    def insert(self, record: VectorRecord) -> str:
        self.records[record.chunk_id] = record
        return record.chunk_id

    def update(self, record: VectorRecord) -> None:
        self.records[record.chunk_id] = record

    def delete(self, chunk_id: str) -> None:
        self.records.pop(chunk_id, None)

    def delete_by_document(self, document_id: str) -> None:
        to_delete = [
            chunk_id
            for chunk_id, record in self.records.items()
            if record.document_id == document_id
        ]
        for chunk_id in to_delete:
            self.records.pop(chunk_id, None)

    def search(self, query: VectorSearchQuery) -> list[VectorSearchResult]:
        results: list[VectorSearchResult] = []
        for record in self.records.values():
            score = _cosine_similarity(query.vector, record.vector)
            if score < query.similarity_threshold:
                continue
            if (
                query.filters
                and query.filters.source_type
                and record.metadata.get("source_type") != query.filters.source_type
            ):
                continue
            results.append(
                VectorSearchResult(
                    chunk_id=record.chunk_id,
                    document_id=record.document_id,
                    score=score,
                    metadata=record.metadata,
                )
            )
        results.sort(key=lambda item: item.score, reverse=True)
        return results[: query.top_k]

    def health_check(self) -> bool:
        return self.healthy

    def count(self) -> int:
        return len(self.records)


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
