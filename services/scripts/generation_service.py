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
from apps.scheduler.models import Job
from domain.llm.dtos import LLMRequest
from domain.scripts.exceptions import ScriptGenerationError, ScriptValidationError
from domain.scripts.schema import PodcastScriptSchema, ScriptSegmentSchema
from services.scripts.duration_estimator import estimate_segment_duration_seconds
from services.scripts.prompt_builder import ScriptPromptBuilder, ScriptPromptConfig
from services.scripts.validation_service import (
    ScriptValidationConfig,
    ScriptValidationResult,
    ScriptValidationService,
)
from services.scripts.version_service import ScriptVersionService
from services.jobs.job_service import JobService
from services.episodes.status_sync import sync_episode_idle_status
from services.knowledge.script_rag import ScriptRagResult, ScriptRagService
from services.episodes.title import (
    apply_episode_name,
    is_placeholder_episode_title,
    normalize_episode_name,
)

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
        script_rag_service: ScriptRagService | None = None,
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
        self._script_rag = script_rag_service or ScriptRagService()
        self._last_token_usage: dict[str, int] = {}
        self._last_rag_result: ScriptRagResult | None = None

    def generate(self, episode: Episode, *, job: Job | None = None) -> Script:
        """Generate a new script version for the given episode."""
        job_service = JobService()

        def _progress(value: int) -> None:
            if job is not None:
                job_service.update_progress(job, value)

        _progress(10)
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

        script = self._resolve_or_create_script(
            episode,
            job=job,
            job_service=job_service,
            llm_provider=provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
        _progress(25)

        try:
            _progress(30)
            rag_result = self._script_rag.enrich(episode, articles)
            self._last_rag_result = rag_result
            _progress(35)
            parsed = self._call_llm(episode, articles, rag_result=rag_result)
            _progress(70)
            validation = self._validation.validate(parsed)
            _progress(85)
            script = self._persist_script(
                script=script,
                articles=articles,
                parsed=parsed,
                validation=validation,
                token_usage=self._last_token_usage,
            )
            _progress(95)
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

    def _resolve_or_create_script(
        self,
        episode: Episode,
        *,
        job: Job | None,
        job_service: JobService,
        llm_provider: str,
        model_name: str,
        prompt_version: str,
    ) -> Script:
        """Reuse the job's script on retry; create a new version for fresh runs."""
        if job is not None:
            script_id = job.payload.get("script_id")
            if not script_id:
                legacy = (
                    Script.objects.filter(
                        episode_id=episode.id,
                        status__in=[ScriptStatus.FAILED, ScriptStatus.GENERATING],
                        created_at__gte=job.created_at,
                    )
                    .order_by("version")
                    .first()
                )
                if legacy is not None and legacy.segments.count() == 0:
                    script_id = str(legacy.id)
                    job_service.merge_payload(job, script_id=script_id)

            if script_id:
                existing = Script.objects.filter(
                    pk=script_id,
                    episode_id=episode.id,
                    status__in=[ScriptStatus.FAILED, ScriptStatus.GENERATING],
                ).first()
                if existing is not None:
                    return self._version_service.reset_placeholder_for_retry(
                        existing,
                        llm_provider=llm_provider,
                        model_name=model_name,
                        prompt_version=prompt_version,
                    )

        script = self._version_service.create_version_placeholder(
            episode.id,
            llm_provider=llm_provider,
            model_name=model_name,
            prompt_version=prompt_version,
        )
        if job is not None:
            job_service.merge_payload(job, script_id=str(script.id))
        return script

    def _call_llm(
        self,
        episode: Episode,
        articles: list[Article],
        *,
        rag_result: ScriptRagResult | None = None,
    ) -> PodcastScriptSchema:
        if len(articles) >= 2:
            return self._call_llm_chaptered(episode, articles, rag_result=rag_result)

        system_prompt = self._prompt_builder.build_system_prompt()
        user_prompt = self._prompt_builder.build_user_prompt(
            episode_title=episode.title,
            episode_summary=episode.summary,
            articles=articles,
            rag_context=rag_result.context_text if rag_result else "",
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

    def _call_llm_chaptered(
        self,
        episode: Episode,
        articles: list[Article],
        *,
        rag_result: ScriptRagResult | None = None,
    ) -> PodcastScriptSchema:
        """Generate one chapter per article and merge into a single script.

        A single LLM call saturates well below the long-form target length on
        local models; per-article calls keep each response small enough that
        the model sustains the requested depth for every story.
        """
        system_prompt = self._prompt_builder.build_system_prompt()
        all_titles = [article.title for article in articles]
        chapter_count = len(articles)

        merged_segments: list[ScriptSegmentSchema] = []
        title = episode.title
        summary = episode.summary
        usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        for chapter_number, article in enumerate(articles, start=1):
            user_prompt = self._prompt_builder.build_chapter_user_prompt(
                episode_title=episode.title,
                episode_summary=episode.summary,
                article=article,
                chapter_number=chapter_number,
                chapter_count=chapter_count,
                all_titles=all_titles,
                rag_context=(
                    rag_result.context_text
                    if rag_result and chapter_number == 1
                    else ""
                ),
            )
            request = LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
                max_tokens=self._config.max_token_budget,
            )
            response = self._llm.chat(request)
            usage["prompt_tokens"] += response.prompt_tokens or 0
            usage["completion_tokens"] += response.completion_tokens or 0
            usage["total_tokens"] += response.total_tokens or 0

            chapter = self._validation.parse_json(response.content)
            merged_segments.extend(chapter.segments)
            if chapter_number == 1:
                title = chapter.title or title
                summary = chapter.summary or summary
            logger.info(
                "Script chapter generated",
                extra={
                    "event": "script_chapter_generated",
                    "episode_id": str(episode.id),
                    "chapter": chapter_number,
                    "chapter_count": chapter_count,
                    "segment_count": len(chapter.segments),
                },
            )

        self._last_token_usage = usage
        return PodcastScriptSchema(
            title=title,
            summary=summary,
            segments=merged_segments,
        )

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
        episode = script.episode
        episode_updates: list[str] = []
        if is_placeholder_episode_title(episode.title) or not episode.title.strip():
            episode.title = parsed.title
            episode_updates.append("title")
        if parsed.summary and not episode.summary.strip():
            episode.summary = parsed.summary
            episode_updates.append("summary")
        if episode_updates:
            episode_updates.append("updated_at")
            episode.save(update_fields=episode_updates)

        script.title = ""
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
            "rag": _rag_metadata(self._last_rag_result),
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

        sync_episode_idle_status(script.episode)
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
                update_fields=["validation_results", "generation_notes", "updated_at"],
            )

        sync_episode_idle_status(script.episode)

        logger.error(
            "Script generation failed",
            extra={
                "event": "script_generation_failed",
                "script_id": str(script.id),
                "error": error_message,
            },
        )


def _rag_metadata(rag_result: ScriptRagResult | None) -> dict[str, object]:
    if rag_result is None:
        return {"enabled": False, "chunks_used": 0}
    return {
        "enabled": rag_result.enabled,
        "chunks_used": rag_result.chunks_used,
        "articles_indexed": rag_result.articles_indexed,
        "context_included": bool(rag_result.context_text),
    }
