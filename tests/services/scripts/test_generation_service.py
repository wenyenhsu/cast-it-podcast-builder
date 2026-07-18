"""Tests for script generation service."""

from unittest.mock import MagicMock

import pytest

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import EpisodeArticle, EpisodeStatus
from apps.scripts.models import Script, ScriptStatus, ValidationStatus
from domain.scripts.exceptions import ScriptGenerationError, ScriptValidationError
from domain.scripts.schema import CoherenceScriptSchema, PodcastScriptSchema
from services.scripts.generation_service import (
    ScriptGenerationConfig,
    ScriptGenerationService,
)
from services.scripts.prompt_builder import ScriptPromptBuilder
from services.scripts.settings import ScriptPipelineSettings
from services.scripts.validation_service import (
    ScriptValidationConfig,
    ScriptValidationService,
)
from tests.services.scripts.conftest import (
    build_pipeline_responder,
    build_valid_script_json,
)


def test_generate_creates_script_and_segments(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    script = service.generate(sample_episode)

    assert script.status == ScriptStatus.READY
    assert script.validation_status == ValidationStatus.PASSED
    assert script.title == ""
    assert script.episode.title == "Weekly AI News"
    assert script.segments.count() == 6
    first_segment = script.segments.order_by("sequence").first()
    assert first_segment is not None
    assert first_segment.speaker in {"expert", "beginner"}
    assert first_segment.voice
    assert first_segment.text
    assert first_segment.article_id is not None
    assert script.metadata.source_article_ids
    script.metadata.refresh_from_db()
    assert script.metadata.is_active is True
    assert script.metadata.token_usage["total_tokens"] == 1800

    sample_episode.refresh_from_db()
    assert sample_episode.status == EpisodeStatus.DRAFT
    assert mock_llm.chat.call_count == 6


def test_generate_without_articles_raises(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    sample_episode.articles.clear()
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    with pytest.raises(ScriptGenerationError, match="no selected articles"):
        service.generate(sample_episode)


def test_generate_marks_script_failed_on_validation_error(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    mock_llm.chat.side_effect = build_pipeline_responder(segment_count=2)
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    with pytest.raises(ScriptValidationError):
        service.generate(sample_episode)

    script = Script.objects.get(episode=sample_episode)
    assert script.status == ScriptStatus.FAILED
    assert script.validation_status == ValidationStatus.FAILED


def test_generate_uses_json_mode(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    service.generate(sample_episode)
    assert all(call.args[0].json_mode is True for call in mock_llm.chat.call_args_list)
    assert all(call.args[0].json_schema for call in mock_llm.chat.call_args_list)
    assert [call.args[0].max_tokens for call in mock_llm.chat.call_args_list] == [
        1200,
        1600,
        2600,
        900,
        6000,
        900,
    ]


def test_generate_uses_episode_language(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    sample_episode.language = "zh-TW"
    sample_episode.save(update_fields=["language"])
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )

    service.generate(sample_episode)

    assert all(
        "lang=zh-TW" in call.args[0].system_prompt
        for call in mock_llm.chat.call_args_list
    )


def test_generate_includes_rag_context_in_prompt(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    from services.knowledge.script_rag import ScriptRagResult, ScriptRagService

    rag_service = MagicMock(spec=ScriptRagService)
    article = sample_episode.articles.first()
    assert article is not None
    article.content = "Long evidence. " * 2000
    article.save(update_fields=["content"])
    rag_service.enrich_article.return_value = ScriptRagResult(
        context_text="Retrieved background on GPT-5.",
        chunks_used=2,
        articles_indexed=1,
        enabled=True,
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
        script_rag_service=rag_service,
    )
    script = service.generate(sample_episode)

    rag_service.enrich_article.assert_called_once()
    assert any(
        "Retrieved background on GPT-5." in call.args[0].user_prompt
        for call in mock_llm.chat.call_args_list
    )
    assert script.metadata.validation_results["rag"]["chunks_used"] == 2


def test_each_long_article_gets_its_own_rag_context(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
    sample_article: Article,
) -> None:
    from services.knowledge.script_rag import ScriptRagResult, ScriptRagService

    sample_article.content = "First article evidence. " * 2000
    sample_article.save(update_fields=["content"])
    second = Article.objects.create(
        source=sample_article.source,
        title="Second source",
        url="https://example.com/second-rag",
        language="en",
        category="AI",
        summary="Second summary.",
        content="Second article evidence. " * 2000,
        content_hash="second-rag-script-article",
        importance_score=80,
        status=ArticleStatus.SELECTED,
    )
    EpisodeArticle.objects.create(episode=sample_episode, article=second)
    rag_service = MagicMock(spec=ScriptRagService)
    rag_service.enrich_article.side_effect = [
        ScriptRagResult("Context for first article.", 1, 1, True),
        ScriptRagResult("Context for second article.", 1, 1, True),
    ]
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
        script_rag_service=rag_service,
    )

    service.generate(sample_episode)

    assert rag_service.enrich_article.call_count == 2
    retrieved_articles = {
        call.args[1].id for call in rag_service.enrich_article.call_args_list
    }
    assert retrieved_articles == {sample_article.id, second.id}
    chapter_prompts = [
        call.args[0].user_prompt
        for call in mock_llm.chat.call_args_list
        if "Article:" in call.args[0].user_prompt
    ]
    assert sum("Context for first article." in item for item in chapter_prompts) == 1
    assert sum("Context for second article." in item for item in chapter_prompts) == 1


def test_outline_controls_article_order_not_title_sort(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
    sample_article: Article,
) -> None:
    second = Article.objects.create(
        source=sample_article.source,
        title="Alphabetically First",
        url="https://example.com/second",
        language="en",
        category="AI",
        summary="A second grounded story.",
        content="The second source provides its own grounded evidence.",
        content_hash="second-script-article",
        importance_score=10,
        status=ArticleStatus.SELECTED,
    )
    EpisodeArticle.objects.create(episode=sample_episode, article=second)
    mock_llm.chat.side_effect = build_pipeline_responder(
        segment_count=6, reverse_outline=True
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )

    script = service.generate(sample_episode)

    first_segment = script.segments.order_by("sequence").first()
    assert first_segment is not None
    assert first_segment.article_id == second.id


def test_outline_paraphrases_are_deferred_to_grounded_critic(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    mock_llm.chat.side_effect = build_pipeline_responder(unsupported_outline_fact=True)
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )

    script = service.generate(sample_episode)

    assert script.status == ScriptStatus.READY


def test_failed_critic_triggers_bounded_rewrite(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    failed = {
        "passed": False,
        "score": 40,
        "missing_facts": ["Release date"],
        "unsupported_claims": [],
        "repetitions": [],
        "dialogue_issues": ["Mechanical Q&A"],
        "coherence_issues": [],
        "transition_issues": [],
        "language_issues": [],
        "rewrite_instructions": ["Add the grounded release fact."],
    }
    passed = {
        **failed,
        "passed": True,
        "score": 90,
        "missing_facts": [],
        "dialogue_issues": [],
    }
    mock_llm.chat.side_effect = build_pipeline_responder(
        critic_payloads=[failed, passed]
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )

    service.generate(sample_episode)

    assert mock_llm.chat.call_count == 8
    assert any(
        "Add the grounded release fact." in call.args[0].user_prompt
        for call in mock_llm.chat.call_args_list
    )


def test_critic_retry_limit_stops_generation(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    failed = {
        "passed": False,
        "score": 20,
        "missing_facts": [],
        "unsupported_claims": ["Invented number"],
        "repetitions": [],
        "dialogue_issues": [],
        "coherence_issues": [],
        "transition_issues": [],
        "language_issues": [],
        "rewrite_instructions": ["Remove the invented number."],
    }
    mock_llm.chat.side_effect = build_pipeline_responder(
        critic_payloads=[failed, failed]
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
        config=ScriptGenerationConfig(
            pipeline_settings=ScriptPipelineSettings(rewrite_retries=1)
        ),
    )

    with pytest.raises(ScriptValidationError, match="Invented number"):
        service.generate(sample_episode)

    assert mock_llm.chat.call_count == 6


def test_critic_retry_limit_accepts_grounded_editorial_warnings(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    editorial_only = {
        "passed": False,
        "score": 60,
        "missing_facts": [],
        "unsupported_claims": [],
        "repetitions": ["The opening repeats the price."],
        "dialogue_issues": ["A question feels leading."],
        "coherence_issues": [],
        "transition_issues": ["The hand-off is abrupt."],
        "language_issues": [],
        "rewrite_instructions": ["Vary the wording and smooth the hand-off."],
    }
    mock_llm.chat.side_effect = build_pipeline_responder(
        critic_payloads=[editorial_only, editorial_only]
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
        config=ScriptGenerationConfig(
            pipeline_settings=ScriptPipelineSettings(rewrite_retries=1)
        ),
    )

    script = service.generate(sample_episode)

    assert script.status == ScriptStatus.READY
    assert mock_llm.chat.call_count == 8


def test_post_coherence_critic_triggers_rewrite(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    passed = {
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
    failed_after_coherence = {
        **passed,
        "passed": False,
        "score": 50,
        "unsupported_claims": ["The coherence pass introduced a number."],
        "rewrite_instructions": ["Remove the unsupported number."],
    }
    mock_llm.chat.side_effect = build_pipeline_responder(
        critic_payloads=[passed, failed_after_coherence, passed]
    )
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )

    script = service.generate(sample_episode)

    assert mock_llm.chat.call_count == 8
    assert any(
        "Remove the unsupported number." in call.args[0].user_prompt
        for call in mock_llm.chat.call_args_list
    )
    assert script.metadata.validation_results["pipeline"]["critics"][0]["passed"]


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("order", "changed segment order"),
        ("voice", "changed a segment speaker or voice"),
    ],
)
def test_coherence_rejects_changed_segment_identity(
    mutation: str,
    message: str,
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
) -> None:
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
    )
    original = PodcastScriptSchema.model_validate_json(
        build_valid_script_json(segment_count=4)
    )
    payload = original.model_dump()
    for index, segment in enumerate(payload["segments"]):
        segment["segment_index"] = index
    if mutation == "order":
        payload["segments"][0]["segment_index"] = 1
        payload["segments"][1]["segment_index"] = 0
    else:
        payload["segments"][0]["voice"] = "different_voice"
    coherence = CoherenceScriptSchema.model_validate(payload)

    with pytest.raises(ScriptValidationError, match=message):
        service._accept_coherence_result(coherence, original)


@pytest.mark.django_db
def test_generate_reuses_failed_script_on_job_retry(
    mock_llm: MagicMock,
    script_prompt_builder: ScriptPromptBuilder,
    sample_episode: object,
) -> None:
    from apps.scheduler.models import Job, JobType

    mock_llm.chat.side_effect = build_pipeline_responder(segment_count=2)
    service = ScriptGenerationService(
        llm_service=mock_llm,
        prompt_builder=script_prompt_builder,
        validation_service=ScriptValidationService(
            config=ScriptValidationConfig(min_segments=4, max_segments=20)
        ),
    )
    job = Job.objects.create(
        job_type=JobType.GENERATE_SCRIPT,
        payload={"episode_id": str(sample_episode.id)},
    )

    with pytest.raises(ScriptValidationError):
        service.generate(sample_episode, job=job)

    job.refresh_from_db()
    failed_script = Script.objects.get(episode=sample_episode)
    assert failed_script.status == ScriptStatus.FAILED
    assert failed_script.version == 1
    assert job.payload["script_id"] == str(failed_script.id)

    mock_llm.chat.side_effect = build_pipeline_responder(segment_count=6)
    script = service.generate(sample_episode, job=job)

    assert Script.objects.filter(episode=sample_episode).count() == 1
    assert script.id == failed_script.id
    assert script.version == 1
    assert script.status == ScriptStatus.READY
    assert script.segments.count() == 6
