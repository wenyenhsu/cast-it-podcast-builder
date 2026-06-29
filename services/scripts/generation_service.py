"""Podcast script generation orchestration service."""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.articles.models import Article
from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptSegment, ScriptStatus, ValidationStatus
from domain.llm.dtos import LLMRequest
from domain.scripts.exceptions import ScriptGenerationError, ScriptValidationError
from domain.scripts.schema import PodcastScriptSchema
from services.scripts.duration_estimator import estimate_segment_duration_seconds
from services.scripts.prompt_builder import ScriptPromptBuilder, ScriptPromptConfig
from services.scripts.validation_service import (
    ScriptValidationConfig,
    ScriptValidationResult,
    ScriptValidationService,
)
from services.scripts.version_service import ScriptVersionService

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScriptGenerationConfig:
    """Configuration for script generation limits."""

    prompt_config: ScriptPromptConfig | None = None
    validation_config: ScriptValidationConfig | None = None
    max_token_budget: int | None = None
    activate_on_success: bool = True


class ScriptGenerationService:
    """Generates validated podcast scripts from episode articles."""

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_builder: ScriptPromptBuilder | None = None,
        validation_service: ScriptValidationService | None = None,
        version_service: ScriptVersionService | None = None,
        config: ScriptGenerationConfig | None = None,
    ) -> None:
        self._llm = llm_service
        self._config = config or ScriptGenerationConfig()
        self._prompt_builder = prompt_builder or ScriptPromptBuilder(
            config=self._config.prompt_config or ScriptPromptConfig()
        )
        self._validation = validation_service or ScriptValidationService(
            config=self._config.validation_config or ScriptValidationConfig()
        )
        self._version_service = version_service or ScriptVersionService()
        self._last_token_usage: dict[str, int] = {}

    def generate(self, episode: Episode) -> Script:
        """Generate a new script version for the given episode."""
        articles = list(episode.articles.prefetch_related("tags").order_by("title"))
        if not articles:
            raise ScriptGenerationError(
                f"Episode {episode.id} has no selected articles for script generation."
            )

        started = time.perf_counter()
        llm_settings = self._llm.settings
        provider = llm_settings.provider
        model_name = llm_settings.chat_model
        prompt_version = self._prompt_builder.prompt_version

        logger.info(
            "Script generation started",
            extra={
                "event": "script_generation_started",
                "episode_id": str(episode.id),
                "article_count": len(articles),
                "prompt_version": prompt_version,
                "llm_provider": provider,
                "model_name": model_name,
            },
        )

        episode.status = EpisodeStatus.GENERATING_SCRIPT
        episode.save(update_fields=["status", "updated_at"])

        script = self._version_service.create_version_placeholder(
            episode.id,
            llm_provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )

        try:
            parsed = self._call_llm(episode, articles)
            validation = self._validation.validate(parsed)
            script = self._persist_script(
                script=script,
                articles=articles,
                parsed=parsed,
                validation=validation,
                token_usage=self._last_token_usage,
            )
        except (ScriptGenerationError, ScriptValidationError) as exc:
            self._mark_failed(script, str(exc))
            raise
        except Exception as exc:
            self._mark_failed(script, str(exc))
            logger.exception(
                "Script generation failed unexpectedly",
                extra={
                    "event": "script_generation_error",
                    "episode_id": str(episode.id),
                    "script_id": str(script.id),
                },
            )
            raise ScriptGenerationError(str(exc)) from exc

        elapsed = time.perf_counter() - started
        logger.info(
            "Script generation completed",
            extra={
                "event": "script_generation_completed",
                "episode_id": str(episode.id),
                "script_id": str(script.id),
                "version": script.version,
                "estimated_duration_seconds": script.estimated_duration_seconds,
                "generation_time_seconds": round(elapsed, 3),
            },
        )
        return script

    def _call_llm(
        self,
        episode: Episode,
        articles: list[Article],
    ) -> PodcastScriptSchema:
        system_prompt = self._prompt_builder.build_system_prompt()
        user_prompt = self._prompt_builder.build_user_prompt(
            episode_title=episode.title,
            episode_summary=episode.summary,
            articles=articles,
        )

        request = LLMRequest(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            max_tokens=self._config.max_token_budget,
        )
        response = self._llm.chat(request)
        self._last_token_usage = {
            "prompt_tokens": response.prompt_tokens,
            "completion_tokens": response.completion_tokens,
            "total_tokens": response.total_tokens,
        }
        return self._validation.parse_json(response.content)

    @transaction.atomic
    def _persist_script(
        self,
        *,
        script: Script,
        articles: list[Article],
        parsed: PodcastScriptSchema,
        validation: ScriptValidationResult,
        token_usage: dict[str, int],
    ) -> Script:
        script.title = parsed.title
        script.status = ScriptStatus.READY
        script.validation_status = ValidationStatus.PASSED
        script.estimated_duration_seconds = validation.estimated_duration_seconds
        script.generated_at = timezone.now()
        script.save(
            update_fields=[
                "title",
                "status",
                "validation_status",
                "estimated_duration_seconds",
                "generated_at",
                "updated_at",
            ]
        )

        ScriptSegment.objects.filter(script=script).delete()
        wpm = (
            self._config.validation_config.words_per_minute
            if self._config.validation_config
            else ScriptValidationConfig().words_per_minute
        )
        segments = [
            ScriptSegment(
                script=script,
                sequence=index,
                speaker=segment.speaker,
                voice=segment.voice,
                emotion=segment.emotion,
                text=segment.text,
                pause_before_seconds=segment.pause_before_seconds,
                pause_after_seconds=segment.pause_after_seconds,
                estimated_duration_seconds=estimate_segment_duration_seconds(
                    segment,
                    words_per_minute=wpm,
                ),
            )
            for index, segment in enumerate(parsed.segments, start=1)
        ]
        ScriptSegment.objects.bulk_create(segments)

        metadata = script.metadata
        metadata.source_article_ids = [str(article.id) for article in articles]
        metadata.selected_topics = sorted(
            {article.category for article in articles if article.category}
        )
        metadata.token_usage = token_usage
        metadata.validation_results = {
            "passed": validation.passed,
            "errors": validation.errors,
            "warnings": validation.warnings,
            "segment_count": validation.segment_count,
            "estimated_duration_seconds": validation.estimated_duration_seconds,
        }
        metadata.generation_notes = parsed.summary
        metadata.save(
            update_fields=[
                "source_article_ids",
                "selected_topics",
                "token_usage",
                "validation_results",
                "generation_notes",
            ]
        )

        if self._config.activate_on_success:
            self._version_service.activate_script(script)

        return script

    def _mark_failed(self, script: Script, error_message: str) -> None:
        script.status = ScriptStatus.FAILED
        script.validation_status = ValidationStatus.FAILED
        script.save(update_fields=["status", "validation_status", "updated_at"])

        metadata = getattr(script, "metadata", None)
        if metadata is not None:
            metadata.validation_results = {"passed": False, "errors": [error_message]}
            metadata.generation_notes = error_message
            metadata.save(
                update_fields=["validation_results", "generation_notes"],
            )

        logger.error(
            "Script generation failed",
            extra={
                "event": "script_generation_failed",
                "script_id": str(script.id),
                "error": error_message,
            },
        )
