"""Abstract vector store interface."""

from abc import ABC, abstractmethod

from infrastructure.vector.types import (
    VectorRecord,
    VectorSearchQuery,
    VectorSearchResult,
)


class BaseVectorStore(ABC):
    """Provider-agnostic vector store abstraction."""

    @abstractmethod
    def insert(self, record: VectorRecord) -> str:
        """Insert a vector record and return its identifier."""

    @abstractmethod
    def update(self, record: VectorRecord) -> None:
        """Update an existing vector record."""

    @abstractmethod
    def delete(self, chunk_id: str) -> None:
        """Delete a vector record by chunk identifier."""

    @abstractmethod
    def delete_by_document(self, document_id: str) -> None:
        """Delete all vector records belonging to a document."""

    @abstractmethod
    def search(self, query: VectorSearchQuery) -> list[VectorSearchResult]:
        """Perform semantic similarity search."""

    @abstractmethod
    def health_check(self) -> bool:
        """Verify the vector store is reachable and operational."""

    @abstractmethod
    def count(self) -> int:
        """Return the number of indexed vectors."""
