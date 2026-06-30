"""Knowledge / RAG application settings."""

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class KnowledgeSettings:
    """Application-level RAG configuration loaded from environment variables."""

    top_k: int
    similarity_threshold: float
    max_context_tokens: int
    chunk_size: int
    chunk_overlap: int
    embedding_dimensions: int
    embedding_batch_size: int
    vector_store: str
    embedding_retry_count: int

    @classmethod
    def from_django_settings(cls) -> "KnowledgeSettings":
        """Load settings from Django configuration."""
        return cls(
            top_k=int(getattr(settings, "RAG_TOP_K", 10)),
            similarity_threshold=float(
                getattr(settings, "RAG_SIMILARITY_THRESHOLD", 0.7)
            ),
            max_context_tokens=int(getattr(settings, "RAG_MAX_CONTEXT_TOKENS", 4000)),
            chunk_size=int(getattr(settings, "RAG_CHUNK_SIZE", 512)),
            chunk_overlap=int(getattr(settings, "RAG_CHUNK_OVERLAP", 50)),
            embedding_dimensions=int(
                getattr(settings, "RAG_EMBEDDING_DIMENSIONS", 768)
            ),
            embedding_batch_size=int(getattr(settings, "RAG_EMBEDDING_BATCH_SIZE", 32)),
            vector_store=getattr(settings, "RAG_VECTOR_STORE", "pgvector"),
            embedding_retry_count=int(
                getattr(settings, "RAG_EMBEDDING_RETRY_COUNT", 3)
            ),
        )
