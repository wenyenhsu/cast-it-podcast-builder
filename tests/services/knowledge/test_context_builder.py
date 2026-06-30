"""Tests for context builder."""

from unittest.mock import MagicMock

from domain.knowledge.dtos import RetrievalResult, RetrievedChunk
from services.knowledge.context_builder import ContextBuilder


def test_context_builder_deduplicates_and_respects_budget(knowledge_settings) -> None:
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        query="ai podcast",
        chunks=[
            RetrievedChunk(
                chunk_id="1",
                document_id="d1",
                source_type="article",
                source_id="a1",
                title="Title A",
                text="Duplicate content about AI.",
                score=0.9,
                token_count=30,
            ),
            RetrievedChunk(
                chunk_id="2",
                document_id="d1",
                source_type="article",
                source_id="a1",
                title="Title A",
                text="Duplicate content about AI.",
                score=0.8,
                token_count=30,
            ),
            RetrievedChunk(
                chunk_id="3",
                document_id="d2",
                source_type="episode",
                source_id="e1",
                title="Episode",
                text="Additional episode context.",
                score=0.7,
                token_count=40,
            ),
        ],
        retrieval_latency_ms=10.0,
        vector_search_duration_ms=5.0,
    )

    builder = ContextBuilder(knowledge_settings, retrieval_service=retrieval)
    context = builder.build("ai podcast", max_context_tokens=100)

    assert context.chunks_retrieved == 3
    assert context.chunks_used == 2
    assert "Duplicate content about AI." in context.context_text
    assert context.total_tokens <= 100


def test_context_builder_ranks_by_score(knowledge_settings) -> None:
    retrieval = MagicMock()
    retrieval.retrieve.return_value = RetrievalResult(
        query="rank test",
        chunks=[
            RetrievedChunk(
                chunk_id="low",
                document_id="d1",
                source_type="article",
                source_id="a1",
                title="Low",
                text="Low score chunk.",
                score=0.2,
                token_count=10,
            ),
            RetrievedChunk(
                chunk_id="high",
                document_id="d2",
                source_type="article",
                source_id="a2",
                title="High",
                text="High score chunk.",
                score=0.9,
                token_count=10,
            ),
        ],
        retrieval_latency_ms=1.0,
        vector_search_duration_ms=1.0,
    )

    builder = ContextBuilder(knowledge_settings, retrieval_service=retrieval)
    context = builder.build("rank test", max_context_tokens=50)

    assert context.blocks[0].chunk_id == "high"
