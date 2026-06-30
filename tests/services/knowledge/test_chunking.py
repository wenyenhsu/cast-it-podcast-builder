"""Tests for chunking service."""

import pytest

from domain.knowledge.exceptions import ChunkingError
from services.knowledge.chunking import ChunkingService


def test_chunk_document_preserves_paragraphs(knowledge_settings) -> None:
    service = ChunkingService(knowledge_settings)
    content = "First paragraph.\n\nSecond paragraph with more detail."

    chunks = service.chunk_document(content)

    assert len(chunks) >= 1
    assert all(chunk.sequence >= 1 for chunk in chunks)
    assert all(chunk.token_count > 0 for chunk in chunks)


def test_chunk_document_overlap(knowledge_settings) -> None:
    settings = knowledge_settings
    service = ChunkingService(settings)
    content = "A" * (settings.chunk_size + 50)

    chunks = service.chunk_document(content)

    assert len(chunks) >= 2


def test_empty_document_raises(knowledge_settings) -> None:
    service = ChunkingService(knowledge_settings)
    with pytest.raises(ChunkingError):
        service.chunk_document("   ")


def test_estimate_tokens(knowledge_settings) -> None:
    service = ChunkingService(knowledge_settings)
    assert service.estimate_tokens("one two three four") >= 4
