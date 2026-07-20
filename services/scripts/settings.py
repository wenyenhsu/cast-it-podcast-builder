"""Settings for the multi-stage podcast script generation pipeline."""

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class ScriptPipelineSettings:
    """Token budgets and quality thresholds, overridable by environment."""

    source_max_tokens: int = 3500
    brief_max_tokens: int = 1200
    outline_max_tokens: int = 1600
    chapter_max_tokens: int = 2600
    critic_max_tokens: int = 900
    coherence_max_tokens: int = 6000
    critic_threshold: int = 75
    rewrite_retries: int = 1
    post_coherence_critic: bool = False

    @classmethod
    def from_django_settings(cls) -> "ScriptPipelineSettings":
        return cls(
            source_max_tokens=int(getattr(settings, "SCRIPT_SOURCE_MAX_TOKENS", 3500)),
            brief_max_tokens=int(getattr(settings, "SCRIPT_BRIEF_MAX_TOKENS", 1200)),
            outline_max_tokens=int(
                getattr(settings, "SCRIPT_OUTLINE_MAX_TOKENS", 1600)
            ),
            chapter_max_tokens=int(
                getattr(settings, "SCRIPT_CHAPTER_MAX_TOKENS", 2600)
            ),
            critic_max_tokens=int(getattr(settings, "SCRIPT_CRITIC_MAX_TOKENS", 900)),
            coherence_max_tokens=int(
                getattr(settings, "SCRIPT_COHERENCE_MAX_TOKENS", 6000)
            ),
            critic_threshold=int(getattr(settings, "SCRIPT_CRITIC_THRESHOLD", 75)),
            rewrite_retries=int(getattr(settings, "SCRIPT_REWRITE_RETRIES", 1)),
            post_coherence_critic=bool(
                getattr(settings, "SCRIPT_POST_COHERENCE_CRITIC", False)
            ),
        )
