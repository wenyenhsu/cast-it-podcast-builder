"""Tests for pgvector retrieval filters."""

from unittest.mock import MagicMock

from domain.knowledge.dtos import RetrievalFilter
from infrastructure.vector.pgvector import _apply_filters


def test_apply_filters_constrains_source_id() -> None:
    queryset = MagicMock()

    result = _apply_filters(
        queryset,
        RetrievalFilter(source_id="article-123"),
    )

    queryset.filter.assert_called_once_with(document__source_id="article-123")
    assert result is queryset.filter.return_value
