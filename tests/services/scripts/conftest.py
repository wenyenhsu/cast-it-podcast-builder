"""Shared fixtures for script service tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus, Tag
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import NewsSource, ProviderType
from domain.llm.dtos import LLMResponse
from services.llm.prompt_builder import PromptBuilder
from services.llm.service import LLMService
from services.llm.settings import LLMSettings
from services.scripts.prompt_builder import ScriptPromptBuilder, ScriptPromptConfig


def build_valid_script_json(*, segment_count: int = 6) -> str:
    """Build a valid podcast script JSON payload for tests."""
    segments = []
    for index in range(segment_count):
        speaker = "expert" if index % 2 == 0 else "beginner"
        segments.append(
            {
                "speaker": speaker,
                "voice": f"{speaker}_voice",
                "emotion": "calm" if speaker == "expert" else "curious",
                "text": (
                    f"This is segment {index + 1} with enough words "
                    "to estimate duration."
                ),
                "pause_before_seconds": 0.0,
                "pause_after_seconds": 0.5,
            }
        )
    payload = {
        "title": "AI Weekly Roundup",
        "summary": "Expert and beginner discuss the latest AI news.",
        "segments": segments,
    }
    return json.dumps(payload)


@pytest.fixture
def script_prompt_builder(tmp_path: Path) -> ScriptPromptBuilder:
    templates_dir = tmp_path / "prompts"
    templates_dir.mkdir()
    (templates_dir / "podcast_script_system.md").write_text(
        "System v{prompt_version} lang={language} tone={tone} "
        "min={min_segments} max={max_segments} intro={include_intro_outro}\n"
        "{expert_persona}\n{beginner_persona}\n{validation_rules}",
        encoding="utf-8",
    )
    (templates_dir / "podcast_script_user.md").write_text(
        "Episode: {episode_title}\nSummary: {episode_summary}\n"
        "Articles: {articles_block}\nSchema: {output_schema}",
        encoding="utf-8",
    )
    (templates_dir / "persona_expert.md").write_text(
        "Expert persona rules.",
        encoding="utf-8",
    )
    (templates_dir / "persona_beginner.md").write_text(
        "Beginner persona rules.",
        encoding="utf-8",
    )
    (templates_dir / "script_validation.md").write_text(
        "Validation rules apply.",
        encoding="utf-8",
    )
    prompt_builder = PromptBuilder(templates_dir=templates_dir)
    return ScriptPromptBuilder(
        prompt_builder=prompt_builder,
        config=ScriptPromptConfig(min_segments=4, max_segments=20),
    )


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock(spec=LLMService)
    llm.settings = LLMSettings(
        provider="ollama",
        base_url="http://localhost:11434",
        chat_model="test-model",
        embedding_model="test-embed",
        temperature=0.7,
        timeout=60.0,
        retry_count=3,
        max_prompt_chars=100_000,
    )
    llm.chat.return_value = LLMResponse(
        content=build_valid_script_json(segment_count=6),
        model="test-model",
        prompt_tokens=100,
        completion_tokens=200,
        total_tokens=300,
    )
    return llm


@pytest.fixture
def news_source(db: None) -> NewsSource:
    return NewsSource.objects.create(
        name="Tech Feed",
        provider_type=ProviderType.RSS,
        enabled=True,
    )


@pytest.fixture
def sample_article(news_source: NewsSource) -> Article:
    article = Article.objects.create(
        source=news_source,
        title="OpenAI Announces GPT-5",
        author="Jane Doe",
        url="https://example.com/gpt-5",
        published_at=timezone.now(),
        language="en",
        category="AI",
        summary="OpenAI released GPT-5 with major improvements.",
        content="OpenAI released GPT-5 with major improvements.",
        content_hash="hash-gpt-5-script",
        importance_score=90,
        status=ArticleStatus.SELECTED,
    )
    tag = Tag.objects.create(name="AI")
    article.tags.add(tag)
    return article


@pytest.fixture
def sample_episode(sample_article: Article) -> Episode:
    episode = Episode.objects.create(
        title="Weekly AI News",
        summary="Top AI stories this week.",
        language="en",
        status=EpisodeStatus.DRAFT,
    )
    EpisodeArticle.objects.create(episode=episode, article=sample_article)
    return episode
