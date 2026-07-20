"""Podcast script generation orchestration service."""

import logging
import time
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from django.db import transaction
from django.utils import timezone
from pydantic import BaseModel

from apps.articles.models import Article
from apps.episodes.models import Episode, EpisodeStatus
from apps.scheduler.models import Job
from apps.scripts.models import Script, ScriptSegment, ScriptStatus, ValidationStatus
from domain.llm.dtos import LLMRequest
from domain.scripts.exceptions import ScriptGenerationError, ScriptValidationError
from domain.scripts.schema import (
    ChapterCriticSchema,
    CoherenceScriptSchema,
    EpisodeOutlineChapterSchema,
    EpisodeOutlineSchema,
    PodcastScriptSchema,
    ScriptSegmentSchema,
    StoryBriefSchema,
)
from services.episodes.status_sync import sync_episode_idle_status
from services.episodes.title import (
    is_placeholder_episode_title,
)
from services.jobs.job_service import JobService
from services.knowledge.script_rag import ScriptRagResult, ScriptRagService
from services.scripts.duration_estimator import estimate_segment_duration_seconds
from services.scripts.prompt_builder import ScriptPromptBuilder, ScriptPromptConfig
from services.scripts.settings import ScriptPipelineSettings
from services.scripts.source_context import clean_article_content, estimate_tokens
from services.scripts.validation_service import (
    ScriptValidationConfig,
    ScriptValidationResult,
    ScriptValidationService,
)
from services.scripts.version_service import ScriptVersionService

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)
SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class ScriptGenerationConfig:
    """Configuration for script generation limits."""

    prompt_config: ScriptPromptConfig | None = None
    validation_config: ScriptValidationConfig | None = None
    max_token_budget: int | None = None
    activate_on_success: bool = True
    pipeline_settings: ScriptPipelineSettings | None = None


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
        self._pipeline = (
            self._config.pipeline_settings
            or ScriptPipelineSettings.from_django_settings()
        )
        self._last_token_usage: dict[str, int] = {}
        self._last_rag_result: ScriptRagResult | None = None
        self._critic_results: list[ChapterCriticSchema] = []
        self._last_pipeline_metadata: dict[str, object] = {}

    def generate(self, episode: Episode, *, job: Job | None = None) -> Script:
        """Generate a new script version for the given episode."""
        job_service = JobService()

        def _progress(value: int) -> None:
            if job is not None:
                job_service.update_progress(job, value)

        _progress(10)
        articles = list(
            episode.articles.prefetch_related("tags").order_by(
                "-importance_score", "-published_at", "created_at"
            )
        )
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
            parsed = self._call_llm(episode, articles)
            _progress(70)
            validation = self._validation.validate(
                parsed,
                critics=self._critic_results,
                expected_language=episode.language,
            )
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
    ) -> PodcastScriptSchema:
        """Run the grounded brief -> outline -> chapter -> critic pipeline."""
        language = episode.language or "en"
        grounding_system_prompt = self._prompt_builder.build_grounding_system_prompt(
            language=language
        )
        self._last_token_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        self._critic_results = []
        self._last_pipeline_metadata = {}

        briefs: list[StoryBriefSchema] = []
        source_by_id: dict[str, str] = {}
        rag_by_id: dict[str, ScriptRagResult] = {}
        for article in articles:
            brief_prompt, source = self._prompt_builder.build_story_brief_prompt(
                article,
                language=language,
                source_max_tokens=self._pipeline.source_max_tokens,
            )
            brief = self._request_schema(
                grounding_system_prompt,
                brief_prompt,
                StoryBriefSchema,
                max_tokens=self._pipeline.brief_max_tokens,
            )
            if brief.article_id != str(article.id):
                raise ScriptGenerationError(
                    f"Story brief returned wrong article ID for {article.id}."
                )
            briefs.append(brief)
            source_by_id[str(article.id)] = source

            cleaned = clean_article_content(article.content or article.summary)
            if estimate_tokens(cleaned) > self._pipeline.source_max_tokens:
                rag_by_id[str(article.id)] = self._script_rag.enrich_article(
                    episode, article
                )

        outline = self._request_schema(
            grounding_system_prompt,
            self._prompt_builder.build_outline_prompt(
                episode_title=episode.title,
                episode_summary=episode.summary,
                language=language,
                briefs=briefs,
            ),
            EpisodeOutlineSchema,
            max_tokens=self._pipeline.outline_max_tokens,
        )
        expected_ids = {str(article.id) for article in articles}
        if set(outline.article_order) != expected_ids:
            raise ScriptGenerationError(
                "Outline must include every episode article exactly once."
            )

        article_by_id = {str(article.id): article for article in articles}
        brief_by_id = {brief.article_id: brief for brief in briefs}
        chapter_plan_by_id = {
            chapter.article_id: chapter for chapter in outline.chapters
        }
        for chapter_plan in outline.chapters:
            grounded_claims = {
                fact.claim
                for fact in brief_by_id[chapter_plan.article_id].must_cover_facts
            }
            unsupported = set(chapter_plan.must_cover_facts) - grounded_claims
            if unsupported:
                logger.warning(
                    "Outline facts were paraphrased or absent from the story brief",
                    extra={
                        "event": "script_outline_fact_mismatch",
                        "article_id": chapter_plan.article_id,
                        "outline_facts": sorted(unsupported),
                    },
                )
        ordered_articles = [article_by_id[item] for item in outline.article_order]
        chapter_count = len(ordered_articles)
        if chapter_count == 1:
            chapter_min = self._prompt_builder.min_segments
            chapter_max = self._prompt_builder.max_segments
        else:
            target_total = max(
                self._prompt_builder.min_segments,
                min(self._prompt_builder.max_segments, 48),
            )
            per_chapter = max(5, min(14, target_total // chapter_count))
            chapter_min = max(4, per_chapter - 1)
            chapter_max = per_chapter + 2
        chapter_system_prompt = self._prompt_builder.build_system_prompt(
            language=language,
            min_segments=chapter_min,
            max_segments=chapter_max,
        )

        merged_segments: list[ScriptSegmentSchema] = []
        chapter_lengths: dict[str, int] = {}
        initial_critics: list[ChapterCriticSchema] = []
        covered: list[str] = []
        previous_summary = "None; this is the first chapter."
        previous_last_lines = "None"
        for chapter_number, article in enumerate(ordered_articles, start=1):
            article_id = str(article.id)
            brief = brief_by_id[article_id]
            chapter_plan = chapter_plan_by_id[article_id]
            next_hook = chapter_plan.transition_out or "Close the episode naturally."
            rag_result = rag_by_id.get(article_id)
            chapter = self._request_schema(
                chapter_system_prompt,
                self._prompt_builder.build_chapter_user_prompt(
                    episode_title=episode.title,
                    episode_summary=episode.summary,
                    article=article,
                    chapter_number=chapter_number,
                    chapter_count=chapter_count,
                    language=language,
                    episode_outline=outline,
                    story_brief=brief,
                    outline_chapter=chapter_plan,
                    source_content=source_by_id[article_id],
                    previous_chapter_summary=previous_summary,
                    previous_chapter_last_lines=previous_last_lines,
                    next_transition_hook=next_hook,
                    already_covered=covered,
                    rag_context=rag_result.context_text if rag_result else "",
                    chapter_min_segments=chapter_min,
                    chapter_max_segments=chapter_max,
                ),
                PodcastScriptSchema,
                max_tokens=self._pipeline.chapter_max_tokens,
            )

            chapter, critic = self._review_and_rewrite_chapter(
                dialogue_system_prompt=chapter_system_prompt,
                grounding_system_prompt=grounding_system_prompt,
                language=language,
                brief=brief,
                chapter_plan=chapter_plan,
                source_content=source_by_id[article_id],
                rag_context=rag_result.context_text if rag_result else "",
                chapter=chapter,
                covered=covered,
                previous_chapter_summary=previous_summary,
                previous_chapter_last_lines=previous_last_lines,
                next_transition_hook=next_hook,
                chapter_number=chapter_number,
            )
            initial_critics.append(critic)
            for segment in chapter.segments:
                segment.article_id = article_id
            merged_segments.extend(chapter.segments)
            chapter_lengths[article_id] = len(chapter.segments)
            previous_summary = chapter.summary
            previous_last_lines = "\n".join(
                segment.text for segment in chapter.segments[-2:]
            )
            covered.extend(chapter_plan.must_cover_facts)
            covered.append(brief.central_claim)

        merged = PodcastScriptSchema(
            title=outline.title or episode.title,
            summary=outline.throughline,
            segments=merged_segments,
        )
        coherence_system_prompt = self._prompt_builder.build_system_prompt(
            language=language,
            min_segments=len(merged.segments),
            max_segments=len(merged.segments),
        )
        coherence_result = self._request_schema(
            coherence_system_prompt,
            self._prompt_builder.build_coherence_prompt(
                language=language,
                outline=outline,
                briefs=briefs,
                script=merged,
            ),
            CoherenceScriptSchema,
            max_tokens=self._pipeline.coherence_max_tokens,
        )
        coherent = self._accept_coherence_result(coherence_result, merged)

        if not self._pipeline.post_coherence_critic:
            self._critic_results = initial_critics
            self._last_rag_result = _aggregate_rag_results(rag_by_id.values())
            self._last_pipeline_metadata = {
                "outline": outline.model_dump(),
                "story_briefs": [brief.model_dump() for brief in briefs],
                "initial_critics": [critic.model_dump() for critic in initial_critics],
                "critics": [critic.model_dump() for critic in initial_critics],
                "post_coherence_critic": False,
            }
            return coherent

        final_segments: list[ScriptSegmentSchema] = []
        final_critics: list[ChapterCriticSchema] = []
        covered = []
        previous_summary = "None; this is the first chapter."
        previous_last_lines = "None"
        offset = 0
        for chapter_number, article in enumerate(ordered_articles, start=1):
            article_id = str(article.id)
            length = chapter_lengths[article_id]
            chapter = PodcastScriptSchema(
                title=coherent.title,
                summary=coherent.summary,
                segments=coherent.segments[offset : offset + length],
            )
            offset += length
            brief = brief_by_id[article_id]
            chapter_plan = chapter_plan_by_id[article_id]
            next_hook = chapter_plan.transition_out or "Close the episode naturally."
            rag_result = rag_by_id.get(article_id)
            chapter, critic = self._review_and_rewrite_chapter(
                dialogue_system_prompt=chapter_system_prompt,
                grounding_system_prompt=grounding_system_prompt,
                language=language,
                brief=brief,
                chapter_plan=chapter_plan,
                source_content=source_by_id[article_id],
                rag_context=rag_result.context_text if rag_result else "",
                chapter=chapter,
                covered=covered,
                previous_chapter_summary=previous_summary,
                previous_chapter_last_lines=previous_last_lines,
                next_transition_hook=next_hook,
                chapter_number=chapter_number,
            )
            for segment in chapter.segments:
                segment.article_id = article_id
            final_segments.extend(chapter.segments)
            final_critics.append(critic)
            previous_summary = chapter.summary
            previous_last_lines = "\n".join(
                segment.text for segment in chapter.segments[-2:]
            )
            covered.extend(chapter_plan.must_cover_facts)
            covered.append(brief.central_claim)

        coherent.segments = final_segments
        self._critic_results = final_critics

        self._last_rag_result = _aggregate_rag_results(rag_by_id.values())
        self._last_pipeline_metadata = {
            "outline": outline.model_dump(),
            "story_briefs": [brief.model_dump() for brief in briefs],
            "initial_critics": [critic.model_dump() for critic in initial_critics],
            "critics": [critic.model_dump() for critic in final_critics],
            "post_coherence_critic": True,
        }
        return coherent

    def _request_schema(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_type: type[SchemaT],
        *,
        max_tokens: int,
    ) -> SchemaT:
        """Call the LLM with an Ollama JSON schema and accumulate usage."""
        response = self._llm.chat(
            LLMRequest(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
                json_schema=schema_type.model_json_schema(),
                max_tokens=(self._config.max_token_budget or max_tokens),
            )
        )
        for key in self._last_token_usage:
            self._last_token_usage[key] += int(getattr(response, key, 0) or 0)
        try:
            return schema_type.model_validate_json(response.content)
        except Exception as exc:
            raise ScriptGenerationError(
                f"Invalid {schema_type.__name__} JSON: {exc}"
            ) from exc

    def _accept_coherence_result(
        self,
        result: CoherenceScriptSchema,
        original: PodcastScriptSchema,
    ) -> PodcastScriptSchema:
        """Verify immutable segment identity before accepting a coherence rewrite."""
        if len(result.segments) != len(original.segments):
            raise ScriptValidationError(
                "Coherence pass changed segment count and broke chapter ownership."
            )
        indices = [segment.segment_index for segment in result.segments]
        if indices != list(range(len(original.segments))):
            raise ScriptValidationError(
                "Coherence pass changed segment order and broke chapter ownership."
            )

        accepted: list[ScriptSegmentSchema] = []
        restored_identity = 0
        for revised, source in zip(result.segments, original.segments, strict=True):
            payload = revised.model_dump(exclude={"segment_index"})
            if revised.speaker != source.speaker or revised.voice != source.voice:
                # Keep text polish; restore immutable TTS identity instead of failing
                # a long multi-stage run on common model drift.
                restored_identity += 1
                payload["speaker"] = source.speaker
                payload["voice"] = source.voice
            segment = ScriptSegmentSchema.model_validate(payload)
            segment.article_id = source.article_id
            accepted.append(segment)
        if restored_identity:
            logger.warning(
                "Coherence pass drifted speaker/voice; restored originals",
                extra={
                    "event": "script_coherence_identity_restored",
                    "restored_segments": restored_identity,
                },
            )
        return PodcastScriptSchema(
            title=result.title,
            summary=result.summary,
            segments=accepted,
        )

    def _review_and_rewrite_chapter(
        self,
        *,
        dialogue_system_prompt: str,
        grounding_system_prompt: str,
        language: str,
        brief: StoryBriefSchema,
        chapter_plan: EpisodeOutlineChapterSchema,
        source_content: str,
        rag_context: str,
        chapter: PodcastScriptSchema,
        covered: list[str],
        previous_chapter_summary: str,
        previous_chapter_last_lines: str,
        next_transition_hook: str,
        chapter_number: int,
    ) -> tuple[PodcastScriptSchema, ChapterCriticSchema]:
        """Critique a chapter and apply bounded, critic-guided rewrites."""
        critic = self._critique_chapter(
            system_prompt=grounding_system_prompt,
            language=language,
            brief=brief,
            chapter_plan=chapter_plan,
            chapter=chapter,
            covered=covered,
        )
        retries = 0
        while not self._critic_passes(critic):
            if retries >= self._pipeline.rewrite_retries:
                if self._critic_is_grounded(critic):
                    logger.warning(
                        "Chapter accepted with editorial warnings after rewrite limit",
                        extra={
                            "event": "script_chapter_editorial_warnings",
                            "chapter_number": chapter_number,
                            "critic_score": critic.score,
                            "issues": self._critic_issues(critic),
                        },
                    )
                    return chapter, critic
                issues = self._critic_issues(critic)
                raise ScriptValidationError(
                    f"Chapter {chapter_number} failed content quality review: "
                    + "; ".join(issues)
                )
            chapter = self._request_schema(
                dialogue_system_prompt,
                self._prompt_builder.build_rewrite_prompt(
                    language=language,
                    brief=brief,
                    outline_chapter=chapter_plan,
                    source_content=source_content,
                    rag_context=rag_context,
                    chapter=chapter,
                    critic=critic,
                    previous_chapter_summary=previous_chapter_summary,
                    previous_chapter_last_lines=previous_chapter_last_lines,
                    next_transition_hook=next_transition_hook,
                    already_covered=covered,
                ),
                PodcastScriptSchema,
                max_tokens=self._pipeline.chapter_max_tokens,
            )
            retries += 1
            critic = self._critique_chapter(
                system_prompt=grounding_system_prompt,
                language=language,
                brief=brief,
                chapter_plan=chapter_plan,
                chapter=chapter,
                covered=covered,
            )
        return chapter, critic

    def _critique_chapter(
        self,
        *,
        system_prompt: str,
        language: str,
        brief: StoryBriefSchema,
        chapter_plan: EpisodeOutlineChapterSchema,
        chapter: PodcastScriptSchema,
        covered: list[str],
    ) -> ChapterCriticSchema:
        return self._request_schema(
            system_prompt,
            self._prompt_builder.build_critic_prompt(
                language=language,
                brief=brief,
                outline_chapter=chapter_plan,
                chapter=chapter,
                already_covered=covered,
            ),
            ChapterCriticSchema,
            max_tokens=self._pipeline.critic_max_tokens,
        )

    def _critic_passes(self, critic: ChapterCriticSchema) -> bool:
        return (
            critic.passed
            and critic.score >= self._pipeline.critic_threshold
            and not critic.missing_facts
            and not critic.unsupported_claims
            and not critic.repetitions
            and not critic.dialogue_issues
            and not critic.coherence_issues
            and not critic.transition_issues
            and critic.language_matches
        )

    @staticmethod
    def _critic_is_grounded(critic: ChapterCriticSchema) -> bool:
        """Allow bounded editorial warnings, never grounding or language failures."""
        return not critic.unsupported_claims and critic.language_matches

    @staticmethod
    def _critic_issues(critic: ChapterCriticSchema) -> list[str]:
        issues = (
            critic.missing_facts
            + critic.unsupported_claims
            + critic.repetitions
            + critic.dialogue_issues
            + critic.coherence_issues
            + critic.transition_issues
            + critic.language_issues
        )
        if not issues:
            issues.append(
                f"critic score {critic.score} is below the required threshold"
            )
        return issues

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
        article_map = {str(article.id): article for article in articles}
        segments = [
            ScriptSegment(
                script=script,
                sequence=index,
                speaker=segment.speaker,
                voice=segment.voice,
                emotion=segment.emotion,
                text=segment.text,
                article=article_map.get(segment.article_id or ""),
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
            "pipeline": self._last_pipeline_metadata,
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


def _aggregate_rag_results(
    results: Iterable[ScriptRagResult],
) -> ScriptRagResult | None:
    items = list(results)
    if not items:
        return None
    return ScriptRagResult(
        context_text="\n\n".join(
            item.context_text for item in items if item.context_text
        ),
        chunks_used=sum(item.chunks_used for item in items),
        articles_indexed=sum(item.articles_indexed for item in items),
        enabled=any(item.enabled for item in items),
    )
