"""Shared fixtures for script service tests."""

import json
import re
from pathlib import Path
from typing import Any
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


def build_pipeline_responder(
    *,
    segment_count: int = 6,
    critic_payloads: list[dict[str, object]] | None = None,
    reverse_outline: bool = False,
    unsupported_outline_fact: bool = False,
) -> object:
    """Return a stage-aware fake for the multi-stage generation pipeline."""
    critics = list(critic_payloads or [])
    chapters: list[dict[str, Any]] = []

    def respond(request: object) -> LLMResponse:
        schema = getattr(request, "json_schema", None) or {}
        title = schema.get("title", "")
        prompt = str(getattr(request, "user_prompt", ""))
        if title == "StoryBriefSchema":
            match = re.search(r"Article ID: ([0-9a-f-]+)", prompt)
            assert match is not None
            content = json.dumps(
                {
                    "article_id": match.group(1),
                    "title": "Grounded story",
                    "summary": "A grounded summary.",
                    "central_claim": "The release improves the product.",
                    "must_cover_facts": [
                        {
                            "claim": "The product was released.",
                            "evidence": "The source says it was released.",
                            "people": [],
                            "dates": [],
                            "numbers": [],
                        }
                    ],
                    "background": [],
                    "uncertainties": [],
                    "unsupported_topics": [],
                    "possible_angles": ["Why the release matters"],
                }
            )
        elif title == "EpisodeOutlineSchema":
            ids = list(
                dict.fromkeys(re.findall(r'"article_id":\s*"([0-9a-f-]+)"', prompt))
            )
            if reverse_outline:
                ids.reverse()
            content = json.dumps(
                {
                    "title": "AI Weekly Roundup",
                    "throughline": "How product releases affect users.",
                    "opening": "Preview the change.",
                    "development": "Explain the evidence.",
                    "closing": "Summarize the implications.",
                    "article_order": ids,
                    "chapters": [
                        {
                            "article_id": article_id,
                            "purpose": "Explain the release.",
                            "must_cover_facts": [
                                (
                                    "The product gained 50% market share."
                                    if unsupported_outline_fact
                                    else "The product was released."
                                )
                            ],
                            "transition_in": "Connect from the prior story.",
                            "transition_out": "Move to the next implication.",
                            "avoid_repeating": [],
                        }
                        for article_id in ids
                    ],
                }
            )
        elif title == "ChapterCriticSchema":
            payload = (
                critics.pop(0)
                if critics
                else {
                    "passed": True,
                    "score": 90,
                    "missing_facts": [],
                    "unsupported_claims": [],
                    "repetitions": [],
                    "dialogue_issues": [],
                    "coherence_issues": [],
                    "transition_issues": [],
                    "language_issues": [],
                    "rewrite_instructions": [],
                }
            )
            content = json.dumps(payload)
        elif title == "CoherenceScriptSchema":
            if chapters:
                merged_segments = [
                    segment for chapter in chapters for segment in chapter["segments"]
                ]
                for index, segment in enumerate(merged_segments):
                    segment["segment_index"] = index
                content = json.dumps(
                    {
                        "title": "AI Weekly Roundup",
                        "summary": "A coherent final episode.",
                        "segments": merged_segments,
                    }
                )
            else:
                raise AssertionError("Coherence requested before any chapters")
        else:
            if "Outline:" in prompt and "Script:" in prompt and chapters:
                raise AssertionError("Coherence request used the wrong schema")
            else:
                payload = json.loads(
                    build_valid_script_json(segment_count=segment_count)
                )
                article_match = re.search(r"ID:\s*([0-9a-f-]+)", prompt)
                if article_match is None:
                    article_match = re.search(r'"article_id":\s*"([0-9a-f-]+)', prompt)
                if article_match:
                    suffix = article_match.group(1)[:8]
                    for segment in payload["segments"]:
                        segment["text"] += f" Source chapter {suffix}."
                if "Article:" in prompt:
                    chapters.append(payload)
                content = json.dumps(payload)
        return LLMResponse(
            content=content,
            model="test-model",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
        )

    return respond


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
    (templates_dir / "podcast_grounding_system.md").write_text(
        "Grounding lang={language} version={prompt_version}", encoding="utf-8"
    )
    (templates_dir / "podcast_script_user.md").write_text(
        "Episode: {episode_title}\nSummary: {episode_summary}\n"
        "Articles: {articles_block}\nRAG: {rag_context_block}\nSchema: {output_schema}",
        encoding="utf-8",
    )
    (templates_dir / "podcast_script_chapter_user.md").write_text(
        "Language: {language}\nOutline: {episode_outline}\nBrief: {story_brief}\n"
        "Article: {articles_block}\nRAG: {rag_context_block}\n"
        "Previous: {previous_chapter_summary}\nLast: {previous_chapter_last_lines}\n"
        "Next: {next_transition_hook}\nCovered: {already_covered}\n"
        "Position: {chapter_position_instructions}\nSchema: {output_schema}",
        encoding="utf-8",
    )
    for name, template in {
        "story_brief_user": (
            "Language: {language}\nArticle ID: {article_id}\nTitle: {article_title}\n"
            "Summary: {article_summary}\nContent: {article_content}\n"
            "Schema: {output_schema}"
        ),
        "episode_outline_user": (
            "Language: {language}\nEpisode: {episode_title}\n"
            "Briefs: {story_briefs}\nSchema: {output_schema}"
        ),
        "chapter_critic_user": (
            "Language: {language}\nBrief: {story_brief}\n"
            "Chapter: {chapter}\nSchema: {output_schema}"
        ),
        "chapter_rewrite_user": (
            "Language: {language}\nBrief: {story_brief}\nCritic: {critic}\n"
            "Chapter: {chapter}\nSchema: {output_schema}"
        ),
        "episode_coherence_user": (
            "Language: {language}\nOutline: {episode_outline}\n"
            "Script: {script}\nSchema: {output_schema}"
        ),
    }.items():
        (templates_dir / f"{name}.md").write_text(template, encoding="utf-8")
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
    llm.chat.side_effect = build_pipeline_responder(segment_count=6)
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
