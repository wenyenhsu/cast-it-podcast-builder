"""Shared fixtures for knowledge service tests."""

import pytest

from apps.providers.models import NewsSource, ProviderType
from services.knowledge.settings import KnowledgeSettings
from tests.services.knowledge.fakes import FakeEmbeddingProvider, FakeVectorStore


@pytest.fixture
def news_source(db: None) -> NewsSource:
    return NewsSource.objects.create(
        name="Tech RSS",
        provider_type=ProviderType.RSS,
        rss_url="https://example.com/feed.xml",
        language="en",
        enabled=True,
    )


@pytest.fixture
def knowledge_settings() -> KnowledgeSettings:
    return KnowledgeSettings(
        top_k=5,
        similarity_threshold=0.1,
        max_context_tokens=200,
        chunk_size=120,
        chunk_overlap=20,
        embedding_dimensions=8,
        embedding_batch_size=4,
        vector_store="pgvector",
        embedding_retry_count=2,
    )


@pytest.fixture
def fake_embedding() -> FakeEmbeddingProvider:
    return FakeEmbeddingProvider(dimensions=8)


@pytest.fixture
def fake_vector_store() -> FakeVectorStore:
    return FakeVectorStore()
