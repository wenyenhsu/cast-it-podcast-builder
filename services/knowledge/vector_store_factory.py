"""Factory for vector store adapters."""

from infrastructure.vector.base import BaseVectorStore
from infrastructure.vector.pgvector import PgVectorStore
from services.knowledge.settings import KnowledgeSettings


class VectorStoreFactory:
    """Creates vector store adapters based on configuration."""

    def __init__(self, settings: KnowledgeSettings | None = None) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()

    def create(self) -> BaseVectorStore:
        store_type = self._settings.vector_store.lower()
        if store_type == "pgvector":
            return PgVectorStore()
        raise ValueError(f"Unsupported vector store: {store_type}")
