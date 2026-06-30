"""Knowledge domain exceptions."""


class KnowledgeException(Exception):
    """Base exception for knowledge layer errors."""


class ChunkingError(KnowledgeException):
    """Raised when document chunking fails."""


class EmbeddingError(KnowledgeException):
    """Raised when embedding generation fails."""


class VectorStoreError(KnowledgeException):
    """Raised when vector store operations fail."""


class RetrievalError(KnowledgeException):
    """Raised when semantic retrieval fails."""


class ContextBuildError(KnowledgeException):
    """Raised when context assembly fails."""
