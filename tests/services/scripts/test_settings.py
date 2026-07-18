"""Tests for multi-stage script pipeline settings."""

from django.test import override_settings

from services.scripts.settings import ScriptPipelineSettings


@override_settings(
    SCRIPT_SOURCE_MAX_TOKENS=100,
    SCRIPT_BRIEF_MAX_TOKENS=200,
    SCRIPT_OUTLINE_MAX_TOKENS=300,
    SCRIPT_CHAPTER_MAX_TOKENS=400,
    SCRIPT_CRITIC_MAX_TOKENS=500,
    SCRIPT_COHERENCE_MAX_TOKENS=600,
    SCRIPT_CRITIC_THRESHOLD=88,
    SCRIPT_REWRITE_RETRIES=2,
)
def test_pipeline_settings_are_overridable() -> None:
    settings = ScriptPipelineSettings.from_django_settings()

    assert settings.source_max_tokens == 100
    assert settings.brief_max_tokens == 200
    assert settings.outline_max_tokens == 300
    assert settings.chapter_max_tokens == 400
    assert settings.critic_max_tokens == 500
    assert settings.coherence_max_tokens == 600
    assert settings.critic_threshold == 88
    assert settings.rewrite_retries == 2
