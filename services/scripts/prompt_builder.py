"""Prompt builder for podcast script generation."""

import html
import json
from dataclasses import dataclass

from apps.articles.models import Article
from domain.scripts.constants import (
    ARTICLE_END,
    ARTICLE_START,
    DEFAULT_LANGUAGE,
    DEFAULT_TONE,
    MAX_SEGMENTS,
    MIN_SEGMENTS,
    PROMPT_VERSION,
)
from services.llm.prompt_builder import PromptBuilder


@dataclass(frozen=True)
class ScriptPromptConfig:
    """Configurable limits injected into script generation prompts."""

    min_segments: int = MIN_SEGMENTS
    max_segments: int = MAX_SEGMENTS
    language: str = DEFAULT_LANGUAGE
    tone: str = DEFAULT_TONE
    include_intro_outro: bool = False
    prompt_version: str = PROMPT_VERSION


class ScriptPromptBuilder:
    """Builds system and user prompts for podcast script generation."""

    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
        config: ScriptPromptConfig | None = None,
    ) -> None:
        self._prompt_builder = prompt_builder or PromptBuilder()
        self._config = config or ScriptPromptConfig()

    @property
    def prompt_version(self) -> str:
        return self._config.prompt_version

    def build_system_prompt(self) -> str:
        """Build the system prompt with persona definitions and JSON rules."""
        expert_persona = self._prompt_builder.load_template("persona_expert")
        beginner_persona = self._prompt_builder.load_template("persona_beginner")
        validation_rules = self._prompt_builder.load_template("script_validation")

        return self._prompt_builder.build_system_prompt(
            "podcast_script_system",
            {
                "expert_persona": expert_persona.strip(),
                "beginner_persona": beginner_persona.strip(),
                "validation_rules": validation_rules.strip(),
                "min_segments": str(self._config.min_segments),
                "max_segments": str(self._config.max_segments),
                "language": self._config.language,
                "tone": self._config.tone,
                "include_intro_outro": str(self._config.include_intro_outro).lower(),
                "prompt_version": self._config.prompt_version,
            },
        )

    def build_user_prompt(
        self,
        episode_title: str,
        episode_summary: str,
        articles: list[Article],
    ) -> str:
        """Build the user prompt with escaped article content."""
        articles_block = self._format_articles(articles)
        output_schema = json.dumps(
            {
                "title": "string",
                "summary": "string",
                "segments": [
                    {
                        "speaker": "expert",
                        "voice": "expert_voice",
                        "emotion": "calm",
                        "text": "string",
                        "pause_before_seconds": 0,
                        "pause_after_seconds": 0,
                    },
                    {
                        "speaker": "beginner",
                        "voice": "beginner_voice",
                        "emotion": "curious",
                        "text": "string",
                        "pause_before_seconds": 0,
                        "pause_after_seconds": 0,
                    },
                ],
            },
            indent=2,
        )

        return self._prompt_builder.build_user_prompt(
            "podcast_script_user",
            {
                "episode_title": self._escape(episode_title),
                "episode_summary": self._escape(episode_summary),
                "articles_block": articles_block,
                "article_count": str(len(articles)),
                "output_schema": output_schema,
                "min_segments": str(self._config.min_segments),
                "max_segments": str(self._config.max_segments),
                "language": self._config.language,
                "tone": self._config.tone,
                "include_intro_outro": str(self._config.include_intro_outro).lower(),
            },
        )

    def _format_articles(self, articles: list[Article]) -> str:
        blocks: list[str] = []
        for index, article in enumerate(articles, start=1):
            tags = ", ".join(tag.name for tag in article.tags.all())
            score = (
                str(article.importance_score)
                if article.importance_score is not None
                else "N/A"
            )
            block = (
                f"{ARTICLE_START}\n"
                f"Article {index}\n"
                f"ID: {article.id}\n"
                f"Title: {self._escape(article.title)}\n"
                f"Category: {self._escape(article.category or 'Uncategorized')}\n"
                f"Tags: {self._escape(tags or 'None')}\n"
                f"Importance Score: {score}\n"
                f"Summary: {self._escape(article.summary or '')}\n"
                f"{ARTICLE_END}"
            )
            blocks.append(block)
        return "\n\n".join(blocks)

    @staticmethod
    def _escape(value: str) -> str:
        """Escape untrusted article text to reduce prompt injection risk."""
        sanitized = value.replace(ARTICLE_START, "").replace(ARTICLE_END, "")
        return html.escape(sanitized, quote=False)
