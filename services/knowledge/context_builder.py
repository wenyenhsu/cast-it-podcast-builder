"""LLM context assembly service."""

import logging

from domain.knowledge.dtos import (
    AssembledContext,
    ContextBlock,
    RetrievalFilter,
    RetrievedChunk,
)
from domain.knowledge.exceptions import ContextBuildError
from services.knowledge.retrieval import RetrievalService
from services.knowledge.settings import KnowledgeSettings

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Builds ranked, deduplicated LLM context from retrieved knowledge."""

    def __init__(
        self,
        settings: KnowledgeSettings | None = None,
        retrieval_service: RetrievalService | None = None,
    ) -> None:
        self._settings = settings or KnowledgeSettings.from_django_settings()
        self._retrieval = retrieval_service or RetrievalService(self._settings)

    def build(
        self,
        query: str,
        *,
        filters: RetrievalFilter | None = None,
        max_context_tokens: int | None = None,
    ) -> AssembledContext:
        """Retrieve, rank, and assemble context for LLM prompting."""
        token_budget = max_context_tokens or self._settings.max_context_tokens
        retrieval = self._retrieval.retrieve(query, filters=filters)
        ranked = _rank_chunks(retrieval.chunks)
        deduplicated = _deduplicate_chunks(ranked)
        selected, context_text = _assemble_within_budget(
            deduplicated,
            token_budget=token_budget,
        )

        blocks = [
            ContextBlock(
                chunk_id=chunk.chunk_id,
                title=chunk.title,
                text=chunk.text,
                score=chunk.score,
                token_count=chunk.token_count,
                source_type=chunk.source_type,
                source_id=chunk.source_id,
            )
            for chunk in selected
        ]

        total_tokens = sum(block.token_count for block in blocks)
        logger.info(
            "Context assembled",
            extra={
                "event": "context_assembled",
                "chunks_retrieved": len(retrieval.chunks),
                "chunks_used": len(blocks),
                "total_tokens": total_tokens,
            },
        )

        return AssembledContext(
            query=query,
            blocks=blocks,
            context_text=context_text,
            total_tokens=total_tokens,
            chunks_retrieved=len(retrieval.chunks),
            chunks_used=len(blocks),
        )


def _rank_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    return sorted(chunks, key=lambda chunk: chunk.score, reverse=True)


def _deduplicate_chunks(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen_text: set[str] = set()
    unique: list[RetrievedChunk] = []
    for chunk in chunks:
        fingerprint = chunk.text.strip().lower()
        if fingerprint in seen_text:
            continue
        seen_text.add(fingerprint)
        unique.append(chunk)
    return unique


def _assemble_within_budget(
    chunks: list[RetrievedChunk],
    *,
    token_budget: int,
) -> tuple[list[RetrievedChunk], str]:
    if token_budget <= 0:
        raise ContextBuildError("Context token budget must be positive.")

    selected: list[RetrievedChunk] = []
    sections: list[str] = []
    used_tokens = 0

    for chunk in chunks:
        if used_tokens + chunk.token_count > token_budget:
            continue
        selected.append(chunk)
        used_tokens += chunk.token_count
        sections.append(
            f"[{chunk.source_type}:{chunk.source_id}] {chunk.title}\n{chunk.text}"
        )

    context_text = "\n\n---\n\n".join(sections)
    return selected, context_text
