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
from domain.scripts.schema import (
    ChapterCriticSchema,
    CoherenceScriptSchema,
    EpisodeOutlineChapterSchema,
    EpisodeOutlineSchema,
    PodcastScriptSchema,
    StoryBriefSchema,
)
from services.llm.prompt_builder import PromptBuilder
from services.scripts.source_context import fit_to_token_budget


@dataclass(frozen=True)
class ScriptPromptConfig:
    """Configurable limits injected into script generation prompts."""

    min_segments: int = MIN_SEGMENTS
    max_segments: int = MAX_SEGMENTS
    language: str = DEFAULT_LANGUAGE
    tone: str = DEFAULT_TONE
    include_intro_outro: bool = True
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

    @property
    def min_segments(self) -> int:
        return self._config.min_segments

    @property
    def max_segments(self) -> int:
        return self._config.max_segments

    def build_system_prompt(
        self,
        *,
        language: str | None = None,
        min_segments: int | None = None,
        max_segments: int | None = None,
    ) -> str:
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
                "min_segments": str(
                    self._config.min_segments if min_segments is None else min_segments
                ),
                "max_segments": str(
                    self._config.max_segments if max_segments is None else max_segments
                ),
                "language": language or self._config.language,
                "tone": self._config.tone,
                "include_intro_outro": str(self._config.include_intro_outro).lower(),
                "prompt_version": self._config.prompt_version,
            },
        )

    def build_grounding_system_prompt(self, *, language: str) -> str:
        """Build non-dialogue system rules for brief, outline, and critic stages."""
        return self._prompt_builder.build_system_prompt(
            "podcast_grounding_system",
            {"language": language, "prompt_version": self._config.prompt_version},
        )

    def build_user_prompt(
        self,
        episode_title: str,
        episode_summary: str,
        articles: list[Article],
        *,
        rag_context: str = "",
    ) -> str:
        """Build the user prompt with escaped article content."""
        articles_block = self._format_articles(articles)
        rag_context_block = self._format_rag_context(rag_context)
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
                "rag_context_block": rag_context_block,
                "article_count": str(len(articles)),
                "output_schema": output_schema,
                "min_segments": str(self._config.min_segments),
                "max_segments": str(self._config.max_segments),
                "language": self._config.language,
                "tone": self._config.tone,
                "include_intro_outro": str(self._config.include_intro_outro).lower(),
            },
        )

    def build_chapter_user_prompt(
        self,
        episode_title: str,
        episode_summary: str,
        article: Article,
        *,
        chapter_number: int,
        chapter_count: int,
        language: str,
        episode_outline: EpisodeOutlineSchema,
        story_brief: StoryBriefSchema,
        outline_chapter: EpisodeOutlineChapterSchema,
        source_content: str,
        previous_chapter_summary: str = "None; this is the first chapter.",
        previous_chapter_last_lines: str = "None",
        next_transition_hook: str = "Close the episode naturally.",
        already_covered: list[str] | None = None,
        rag_context: str = "",
        chapter_min_segments: int = 10,
        chapter_max_segments: int = 14,
    ) -> str:
        """Build a user prompt for one chapter of a multi-article episode."""
        if chapter_number == 1:
            position = (
                "This is the FIRST chapter: open with a short show intro (2 segments) "
                "that greets listeners and previews all the stories listed above, "
                "then cover this chapter's article."
            )
        elif chapter_number == chapter_count:
            position = (
                "This is the LAST chapter: cover this chapter's article, then close "
                "with a short outro (2 segments) wrapping up the whole episode."
            )
        else:
            position = (
                "This is a MIDDLE chapter: transition in naturally from the previous "
                "story and hand off to the next one at the end."
            )

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
                    }
                ],
            },
            indent=2,
        )

        return self._prompt_builder.build_user_prompt(
            "podcast_script_chapter_user",
            {
                "episode_title": self._escape(episode_title),
                "episode_summary": self._escape(episode_summary),
                "language": language,
                "tone": self._config.tone,
                "episode_outline": episode_outline.model_dump_json(indent=2),
                "story_brief": story_brief.model_dump_json(indent=2),
                "chapter_number": str(chapter_number),
                "chapter_count": str(chapter_count),
                "chapter_position_instructions": position,
                "articles_block": self._format_articles(
                    [article], content_by_id={str(article.id): source_content}
                ),
                "rag_context_block": self._format_rag_context(rag_context),
                "previous_chapter_summary": self._escape(previous_chapter_summary),
                "previous_chapter_last_lines": self._escape(
                    previous_chapter_last_lines
                ),
                "next_transition_hook": self._escape(next_transition_hook),
                "already_covered": json.dumps(
                    already_covered or [], ensure_ascii=False
                ),
                "required_facts": json.dumps(
                    outline_chapter.must_cover_facts, ensure_ascii=False
                ),
                "output_schema": output_schema,
                "chapter_min_segments": str(chapter_min_segments),
                "chapter_max_segments": str(chapter_max_segments),
            },
        )

    def build_story_brief_prompt(
        self,
        article: Article,
        *,
        language: str,
        source_max_tokens: int,
    ) -> tuple[str, str]:
        """Build a grounded brief prompt and return its budgeted source text."""
        source = fit_to_token_budget(
            article.content or article.summary,
            source_max_tokens,
        )
        prompt = self._prompt_builder.build_user_prompt(
            "story_brief_user",
            {
                "language": language,
                "article_id": str(article.id),
                "article_title": self._escape(article.title),
                "article_summary": self._escape(article.summary),
                "article_content": self._escape(source),
                "output_schema": json.dumps(
                    StoryBriefSchema.model_json_schema(), ensure_ascii=False
                ),
            },
        )
        return prompt, source

    def build_outline_prompt(
        self,
        *,
        episode_title: str,
        episode_summary: str,
        language: str,
        briefs: list[StoryBriefSchema],
    ) -> str:
        return self._prompt_builder.build_user_prompt(
            "episode_outline_user",
            {
                "language": language,
                "episode_title": self._escape(episode_title),
                "episode_summary": self._escape(episode_summary),
                "story_briefs": json.dumps(
                    [brief.model_dump() for brief in briefs],
                    ensure_ascii=False,
                    indent=2,
                ),
                "output_schema": json.dumps(
                    EpisodeOutlineSchema.model_json_schema(), ensure_ascii=False
                ),
            },
        )

    def build_critic_prompt(
        self,
        *,
        language: str,
        brief: StoryBriefSchema,
        outline_chapter: EpisodeOutlineChapterSchema,
        chapter: PodcastScriptSchema,
        already_covered: list[str],
    ) -> str:
        return self._prompt_builder.build_user_prompt(
            "chapter_critic_user",
            {
                "language": language,
                "story_brief": brief.model_dump_json(indent=2),
                "outline_chapter": outline_chapter.model_dump_json(indent=2),
                "already_covered": json.dumps(already_covered, ensure_ascii=False),
                "expected_transition": outline_chapter.transition_out,
                "chapter": chapter.model_dump_json(indent=2),
                "output_schema": json.dumps(
                    ChapterCriticSchema.model_json_schema(), ensure_ascii=False
                ),
            },
        )

    def build_rewrite_prompt(
        self,
        *,
        language: str,
        brief: StoryBriefSchema,
        outline_chapter: EpisodeOutlineChapterSchema,
        source_content: str,
        rag_context: str,
        chapter: PodcastScriptSchema,
        critic: ChapterCriticSchema,
        previous_chapter_summary: str,
        previous_chapter_last_lines: str,
        next_transition_hook: str,
        already_covered: list[str],
    ) -> str:
        return self._prompt_builder.build_user_prompt(
            "chapter_rewrite_user",
            {
                "language": language,
                "story_brief": brief.model_dump_json(indent=2),
                "outline_chapter": outline_chapter.model_dump_json(indent=2),
                "source_content": self._escape(source_content),
                "rag_context_block": self._format_rag_context(rag_context),
                "previous_chapter_summary": previous_chapter_summary,
                "previous_chapter_last_lines": previous_chapter_last_lines,
                "next_transition_hook": next_transition_hook,
                "already_covered": json.dumps(already_covered, ensure_ascii=False),
                "chapter": chapter.model_dump_json(indent=2),
                "critic": critic.model_dump_json(indent=2),
                "output_schema": json.dumps(
                    PodcastScriptSchema.model_json_schema(), ensure_ascii=False
                ),
            },
        )

    def build_coherence_prompt(
        self,
        *,
        language: str,
        outline: EpisodeOutlineSchema,
        briefs: list[StoryBriefSchema],
        script: PodcastScriptSchema,
    ) -> str:
        indexed_script = script.model_dump()
        for index, segment in enumerate(indexed_script["segments"]):
            segment["segment_index"] = index
        return self._prompt_builder.build_user_prompt(
            "episode_coherence_user",
            {
                "language": language,
                "episode_outline": outline.model_dump_json(indent=2),
                "story_briefs": json.dumps(
                    [brief.model_dump() for brief in briefs], ensure_ascii=False
                ),
                "script": json.dumps(indexed_script, ensure_ascii=False, indent=2),
                "output_schema": json.dumps(
                    CoherenceScriptSchema.model_json_schema(), ensure_ascii=False
                ),
            },
        )

    def _format_articles(
        self,
        articles: list[Article],
        *,
        content_by_id: dict[str, str] | None = None,
    ) -> str:
        blocks: list[str] = []
        for index, article in enumerate(articles, start=1):
            tags = ", ".join(tag.name for tag in article.tags.all())
            score = (
                str(article.importance_score)
                if article.importance_score is not None
                else "N/A"
            )
            content = (content_by_id or {}).get(str(article.id), "")
            block = (
                f"{ARTICLE_START}\n"
                f"Article {index}\n"
                f"ID: {article.id}\n"
                f"Title: {self._escape(article.title)}\n"
                f"Category: {self._escape(article.category or 'Uncategorized')}\n"
                f"Tags: {self._escape(tags or 'None')}\n"
                f"Importance Score: {score}\n"
                f"Summary: {self._escape(article.summary or '')}\n"
                f"Content: {self._escape(content)}\n"
                f"{ARTICLE_END}"
            )
            blocks.append(block)
        return "\n\n".join(blocks)

    def _format_rag_context(self, rag_context: str) -> str:
        cleaned = rag_context.strip()
        if not cleaned:
            return ""
        return (
            "## Retrieved Knowledge (semantic search)\n"
            "The following excerpts were retrieved from the knowledge base. "
            "Treat them as supplemental reference material alongside the "
            "articles below.\n\n"
            f"{self._escape(cleaned)}"
        )

    @staticmethod
    def _escape(value: str) -> str:
        """Escape untrusted article text to reduce prompt injection risk."""
        sanitized = value.replace(ARTICLE_START, "").replace(ARTICLE_END, "")
        return html.escape(sanitized, quote=False)
