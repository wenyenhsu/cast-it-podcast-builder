"""Knowledge base models for RAG indexing and retrieval."""

from django.conf import settings as django_settings
from django.db import models
from pgvector.django import VectorField

from apps.core.models import DomainModel


def _embedding_dimensions() -> int:
    return int(getattr(django_settings, "RAG_EMBEDDING_DIMENSIONS", 768))


class SourceType(models.TextChoices):
    """Supported knowledge document source types."""

    ARTICLE = "article", "Article"
    EPISODE = "episode", "Podcast Episode"
    SCRIPT = "script", "Podcast Script"
    NEWSLETTER = "newsletter", "Newsletter"
    DOCUMENTATION = "documentation", "Documentation"


class EmbeddingStatus(models.TextChoices):
    """Embedding generation status for a knowledge chunk."""

    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    COMPLETED = "completed", "Completed"
    FAILED = "failed", "Failed"


class KnowledgeDocument(DomainModel):
    """Normalized knowledge document indexed for semantic retrieval."""

    source_type = models.CharField(
        max_length=30,
        choices=SourceType.choices,
        db_index=True,
    )
    source_id = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=500)
    language = models.CharField(max_length=10, default="en", db_index=True)
    content = models.TextField()
    checksum = models.CharField(max_length=64, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "source_id"],
                name="unique_knowledge_document_source",
            ),
        ]
        indexes = [
            models.Index(fields=["source_type", "language"]),
            models.Index(fields=["checksum"]),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.source_type})"


class KnowledgeChunk(DomainModel):
    """Text chunk belonging to a knowledge document."""

    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )
    sequence = models.PositiveIntegerField()
    text = models.TextField()
    token_count = models.PositiveIntegerField(default=0)
    embedding_status = models.CharField(
        max_length=20,
        choices=EmbeddingStatus.choices,
        default=EmbeddingStatus.PENDING,
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    embedding = VectorField(dimensions=_embedding_dimensions(), null=True, blank=True)

    class Meta:
        ordering = ["document", "sequence"]
        constraints = [
            models.UniqueConstraint(
                fields=["document", "sequence"],
                name="unique_knowledge_chunk_sequence",
            ),
        ]
        indexes = [
            models.Index(fields=["document", "embedding_status"]),
        ]

    def __str__(self) -> str:
        return f"Chunk {self.sequence} of {self.document_id}"
