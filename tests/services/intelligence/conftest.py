"""Shared fixtures for intelligence service tests."""

from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.providers.models import NewsSource, ProviderType
from domain.llm.dtos import LLMResponse
from services.llm.prompt_builder import PromptBuilder
from services.llm.service import LLMService


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock(spec=LLMService)

    def chat_side_effect(request: object) -> LLMResponse:
        user_prompt = getattr(request, "user_prompt", "")
        if "Classify" in user_prompt:
            content = "AI"
        elif "Extract" in user_prompt and "keywords" in user_prompt.lower():
            content = "OpenAI, GPT-5, LLM, API, Enterprise"
        elif user_prompt.startswith("Rate "):
            content = "85"
        elif user_prompt.startswith("Title for"):
            content = "AI Breakthroughs Today"
        elif user_prompt.startswith("Summary for"):
            content = "A look at the latest AI stories."
        else:
            content = "This is a generated summary for testing."
        return LLMResponse(content=content, model="test-model")

    llm.chat.side_effect = chat_side_effect
    return llm


@pytest.fixture
def prompt_builder(tmp_path: object) -> PromptBuilder:
    from pathlib import Path

    templates_dir = Path(str(tmp_path)) / "prompts"
    templates_dir.mkdir()
    (templates_dir / "system.md").write_text(
        "System for {show_name} in {language}.",
        encoding="utf-8",
    )
    (templates_dir / "summary.md").write_text(
        "Summarize {title}: {content}",
        encoding="utf-8",
    )
    (templates_dir / "classification.md").write_text(
        "Classify {title}: {summary}",
        encoding="utf-8",
    )
    (templates_dir / "keywords.md").write_text(
        "Extract {min_keywords}-{max_keywords} keywords for {title}",
        encoding="utf-8",
    )
    (templates_dir / "importance.md").write_text(
        "Rate {title} published {published_at}",
        encoding="utf-8",
    )
    (templates_dir / "episode_title.md").write_text(
        "Title for {language}: {articles}",
        encoding="utf-8",
    )
    (templates_dir / "episode_summary.md").write_text(
        "Summary for {title}: {articles}",
        encoding="utf-8",
    )
    return PromptBuilder(templates_dir=templates_dir)


@pytest.fixture
def news_source(db: None) -> NewsSource:
    return NewsSource.objects.create(
        name="Tech Feed",
        provider_type=ProviderType.RSS,
        enabled=True,
    )


@pytest.fixture
def sample_article(news_source: NewsSource) -> Article:
    return Article.objects.create(
        source=news_source,
        title="OpenAI Announces GPT-5",
        author="Jane Doe",
        url="https://example.com/gpt-5",
        published_at=timezone.now(),
        language="en",
        content="OpenAI released GPT-5 with major improvements.",
        content_hash="hash-gpt-5",
        status=ArticleStatus.COLLECTED,
    )
