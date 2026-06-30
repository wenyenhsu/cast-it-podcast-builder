"""Tests for knowledge health service."""

from unittest.mock import MagicMock, patch

from services.knowledge.health import KnowledgeHealthService


def test_knowledge_health_all_healthy() -> None:
    with (
        patch(
            "services.knowledge.health.VectorStoreFactory.create",
            return_value=MagicMock(health_check=lambda: True, count=lambda: 5),
        ),
        patch(
            "services.knowledge.health.EmbeddingProviderFactory.create",
            return_value=MagicMock(
                health_check=lambda: True,
                model_name="test-embed",
            ),
        ),
    ):
        result = KnowledgeHealthService().check_all()

    assert result["healthy"] is True
    assert result["vector_store"]["indexed_vectors"] == 5
    assert result["embedding_provider"]["model"] == "test-embed"
