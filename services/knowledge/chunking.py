"""Document chunking service."""

import logging
import re
from typing import Any

from domain.knowledge.dtos import ChunkDraft
from domain.knowledge.exceptions import ChunkingError
from services.knowledge.settings import KnowledgeSettings

logger = logging.getLogger(__name__)

_PARAGRAPH_SPLIT = re.compile(r"\n\s*\n+")


class ChunkingService:
    """Splits documents into overlapping chunks while preserving paragraphs."""

    def __init__(self, settings: KnowledgeSettings | None = None) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()

    def chunk_document(
        self,
        content: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> list[ChunkDraft]:
        """Split document content into ordered chunks."""
        normalized = content.strip()
        if not normalized:
            raise ChunkingError("Document content is empty.")

        paragraphs = [
            paragraph.strip()
            for paragraph in _PARAGRAPH_SPLIT.split(normalized)
            if paragraph.strip()
        ]
        if not paragraphs:
            paragraphs = [normalized]

        chunk_size = self._settings.chunk_size
        overlap = min(self._settings.chunk_overlap, chunk_size - 1)
        chunks: list[ChunkDraft] = []
        buffer = ""
        sequence = 1
        base_metadata = metadata or {}

        for paragraph in paragraphs:
            candidate = f"{buffer}\n\n{paragraph}".strip() if buffer else paragraph
            if len(candidate) <= chunk_size:
                buffer = candidate
                continue

            if buffer:
                chunks.append(self._make_chunk(sequence, buffer, base_metadata))
                sequence += 1
                buffer = _overlap_tail(buffer, overlap)

            while len(paragraph) > chunk_size:
                piece = paragraph[:chunk_size]
                chunks.append(self._make_chunk(sequence, piece, base_metadata))
                sequence += 1
                paragraph = _overlap_tail(piece, overlap) + paragraph[chunk_size:]

            buffer = paragraph

        if buffer:
            chunks.append(self._make_chunk(sequence, buffer, base_metadata))

        logger.info(
            "Chunks created",
            extra={
                "event": "chunks_created",
                "chunk_count": len(chunks),
                "chunk_size": chunk_size,
                "chunk_overlap": overlap,
            },
        )
        return chunks

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count using a character-based heuristic."""
        stripped = text.strip()
        if not stripped:
            return 0
        word_count = len(stripped.split())
        char_estimate = max(1, len(stripped) // 4)
        return max(word_count, char_estimate)

    def _make_chunk(
        self,
        sequence: int,
        text: str,
        metadata: dict[str, Any],
    ) -> ChunkDraft:
        return ChunkDraft(
            sequence=sequence,
            text=text.strip(),
            token_count=self.estimate_tokens(text),
            metadata=dict(metadata),
        )


def _overlap_tail(text: str, overlap: int) -> str:
    if overlap <= 0:
        return ""
    return text[-overlap:]
