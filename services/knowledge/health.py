"""Knowledge layer health checks."""

from typing import Any

from services.knowledge.embedding_factory import EmbeddingProviderFactory
from services.knowledge.settings import KnowledgeSettings
from services.knowledge.vector_store_factory import VectorStoreFactory
from services.llm.settings import LLMSettings


class KnowledgeHealthService:
    """Health checks for vector store and embedding provider."""

    def check_all(self) -> dict[str, Any]:
        vector = self.vector_store()
        embedding = self.embedding_provider()
        healthy = vector.get("healthy", False) and embedding.get("healthy", False)
        return {
            "healthy": healthy,
            "vector_store": vector,
            "embedding_provider": embedding,
        }

    def vector_store(self) -> dict[str, Any]:
        settings = KnowledgeSettings.from_django_settings()
        store = VectorStoreFactory(settings).create()
        healthy = store.health_check()
        return {
            "healthy": healthy,
            "provider": settings.vector_store,
            "indexed_vectors": store.count(),
        }

    def embedding_provider(self) -> dict[str, Any]:
        llm_settings = LLMSettings.from_django_settings()
        provider = EmbeddingProviderFactory(llm_settings).create()
        healthy = provider.health_check()
        return {
            "healthy": healthy,
            "provider": llm_settings.provider,
            "model": provider.model_name,
        }
