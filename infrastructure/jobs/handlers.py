"""Job handler implementations that delegate to business services."""

import logging
from typing import Any

from apps.articles.models import Article
from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode
from apps.scheduler.models import Job
from apps.scripts.models import Script, ScriptStatus
from domain.jobs.exceptions import JobPermanentError, JobTransientError
from domain.jobs.queues import (
    QUEUE_AUDIO,
    QUEUE_INGESTION,
    QUEUE_LLM,
    QUEUE_MONITORING,
    QUEUE_PUBLISHING,
    QUEUE_TTS,
)
from domain.llm.exceptions import (
    LLMException,
    ProviderUnavailableException,
    TimeoutException,
)
from infrastructure.jobs.runner import BaseJobHandler
from services.jobs.job_service import JobService

logger = logging.getLogger(__name__)


def _require_payload_key(job: Job, key: str) -> Any:
    value = job.payload.get(key)
    if value is None:
        raise JobPermanentError(f"Missing required payload key: {key}")
    return value


class ImportNewsHandler(BaseJobHandler):
    job_type = "import_news"
    queue = QUEUE_INGESTION

    def execute(self, job: Job) -> dict[str, Any]:
        from apps.providers.models import NewsSource
        from services.news.import_service import NewsImportService
        from services.news.provider_factory import ProviderFactory

        service = NewsImportService()
        factory = ProviderFactory()
        source_id = job.payload.get("source_id")
        if source_id:
            sources = [NewsSource.objects.get(pk=source_id)]
        else:
            sources = list(NewsSource.objects.filter(enabled=True))

        total_imported = 0
        for source in sources:
            provider = factory.create(source)
            import_result = service.import_from_provider(provider)
            total_imported += import_result.imported
        return {"imported_count": total_imported}


class SummarizeArticleHandler(BaseJobHandler):
    job_type = "summarize_article"
    queue = QUEUE_LLM

    def execute(self, job: Job) -> dict[str, Any]:
        from services.intelligence.summary_service import ArticleSummaryService
        from services.llm.service import LLMService

        article_id = _require_payload_key(job, "article_id")
        article = Article.objects.get(pk=article_id)
        service = ArticleSummaryService(LLMService())
        summary = service.summarize(article)
        if summary is None:
            raise JobPermanentError(f"Article {article_id} could not be summarized.")
        return {"article_id": str(article_id), "summary": summary.summary}


class ClassifyArticleHandler(BaseJobHandler):
    job_type = "classify_article"
    queue = QUEUE_LLM

    def execute(self, job: Job) -> dict[str, Any]:
        from services.intelligence.classification_service import (
            ArticleClassificationService,
        )
        from services.llm.service import LLMService

        article_id = _require_payload_key(job, "article_id")
        article = Article.objects.get(pk=article_id)
        service = ArticleClassificationService(LLMService())
        classification = service.classify(article)
        return {"article_id": str(article_id), "category": classification.category}


class EpisodePlanningHandler(BaseJobHandler):
    job_type = "episode_planning"
    queue = QUEUE_LLM

    def execute(self, job: Job) -> dict[str, Any]:
        from services.intelligence.pipeline import EpisodePlanningPipeline
        from services.llm.service import LLMService

        pipeline_result = EpisodePlanningPipeline(LLMService()).run()
        episode_id = None
        if pipeline_result.episode_plan is not None:
            episode_id = str(pipeline_result.episode_plan.episode_id)
        return {
            "episode_id": episode_id,
            "articles_processed": pipeline_result.articles_processed,
        }


def _resolve_episode_for_script(job: Job) -> Episode:
    """Resolve the episode for a manually queued script job."""
    episode_id = job.payload.get("episode_id")
    if not episode_id:
        raise JobPermanentError(
            "Script generation requires episode_id. "
            "Automatic scheduling is disabled; use Content → Generate Script."
        )
    return Episode.objects.get(pk=episode_id)


class GenerateScriptHandler(BaseJobHandler):
    job_type = "generate_script"
    queue = QUEUE_LLM

    def execute(self, job: Job) -> dict[str, Any]:
        from services.llm.service import LLMService
        from services.scripts.generation_service import ScriptGenerationService

        episode = _resolve_episode_for_script(job)
        JobService().update_progress(job, 5)
        try:
            script = ScriptGenerationService(LLMService()).generate(episode, job=job)
        except (ProviderUnavailableException, TimeoutException) as exc:
            raise JobTransientError(str(exc)) from exc
        except LLMException as exc:
            raise JobPermanentError(str(exc)) from exc
        return {"script_id": str(script.id), "version": script.version}


def _resolve_script_for_audio(job: Job) -> Script:
    script_id = job.payload.get("script_id")
    if script_id:
        return Script.objects.select_related("episode").get(pk=script_id)

    from services.scripts.version_service import ScriptVersionService

    episode_id = job.payload.get("episode_id")
    if episode_id:
        active = ScriptVersionService().get_active_script(episode_id)
        if active is not None:
            return Script.objects.select_related("episode").get(pk=active.id)

        script = (
            Script.objects.filter(
                episode_id=episode_id,
                status__in=[ScriptStatus.READY, ScriptStatus.APPROVED],
            )
            .order_by("-version")
            .first()
        )
        if script is None:
            raise JobPermanentError(
                f"No ready script found for episode {episode_id}."
            )
        return Script.objects.select_related("episode").get(pk=script.id)

    # Scheduled run: newest ready script whose episode has no final audio yet.
    from django.db.models import Exists, OuterRef

    final_audio = AudioAsset.objects.filter(
        episode=OuterRef("episode_id"),
        is_final_episode_audio=True,
        status=AudioAssetStatus.READY,
    )
    script = (
        Script.objects.filter(
            status__in=[ScriptStatus.READY, ScriptStatus.APPROVED],
        )
        .annotate(has_final_audio=Exists(final_audio))
        .filter(has_final_audio=False)
        .select_related("episode")
        .order_by("-created_at")
        .first()
    )
    if script is None:
        raise JobPermanentError("No ready script awaiting audio.")
    return script


class GenerateAudioHandler(BaseJobHandler):
    job_type = "generate_audio"
    queue = QUEUE_TTS

    def execute(self, job: Job) -> dict[str, Any]:
        from domain.audio.exceptions import (
            ProviderUnavailableException as TTSUnavailable,
        )
        from services.audio.generation_service import AudioGenerationService

        script = _resolve_script_for_audio(job)
        script_id = script.id
        try:
            results = AudioGenerationService().generate_for_script(script)
        except TTSUnavailable as exc:
            raise JobTransientError(str(exc)) from exc

        output: dict[str, Any] = {
            "script_id": str(script_id),
            "segment_count": len(results),
        }
        if job.payload.get("scheduled"):
            # Scheduled runs go straight to the final stitched episode so the
            # downstream publish step has audio to ship.
            from services.audio.pipeline.service import AudioPipelineService

            pipeline_result = AudioPipelineService().process_episode(script.episode)
            output["output_path"] = pipeline_result.output_path
            output["duration_seconds"] = pipeline_result.duration_seconds
        return output


class RunAudioPipelineHandler(BaseJobHandler):
    job_type = "run_audio_pipeline"
    queue = QUEUE_AUDIO

    def execute(self, job: Job) -> dict[str, Any]:
        from services.audio.pipeline.service import AudioPipelineService

        episode_id = _require_payload_key(job, "episode_id")
        episode = Episode.objects.get(pk=episode_id)
        result = AudioPipelineService().process_episode(episode)
        return {
            "episode_id": str(episode_id),
            "output_path": result.output_path,
            "duration_seconds": result.duration_seconds,
        }


class PublishEpisodeHandler(BaseJobHandler):
    job_type = "publish_episode"
    queue = QUEUE_PUBLISHING

    def execute(self, job: Job) -> dict[str, Any]:
        from domain.publish.exceptions import PublishValidationError
        from services.publish.service import PublishService

        service = PublishService()
        payload = job.payload or {}

        if payload.get("scheduled"):
            results = service.publish_ready_episodes()
            return {
                "scheduled": True,
                "published_count": len(results),
                "episode_ids": [str(result.episode_id) for result in results],
            }

        episode_id = _require_payload_key(job, "episode_id")
        platforms = payload.get("platforms")
        try:
            result = service.publish_episode(
                episode_id,
                platforms=platforms,
            )
        except PublishValidationError as exc:
            raise JobPermanentError(str(exc)) from exc

        return {
            "episode_id": str(result.episode_id),
            "platforms": [item.platform for item in result.platform_results],
            "published_urls": {
                item.platform: item.published_url for item in result.platform_results
            },
            "publish_job_ids": [str(job_id) for job_id in result.publish_job_ids],
        }


class HealthCheckHandler(BaseJobHandler):
    job_type = "health_check"
    queue = QUEUE_MONITORING

    def execute(self, job: Job) -> dict[str, Any]:
        from infrastructure.celery.health import CeleryHealthService

        return CeleryHealthService().check_all()


class RetryFailedJobsHandler(BaseJobHandler):
    job_type = "retry_job"
    queue = QUEUE_MONITORING

    def __init__(self, job_service: JobService | None = None) -> None:
        self._job_service = job_service or JobService()

    def execute(self, job: Job) -> dict[str, Any]:
        from apps.scheduler.tasks.registry import get_task_for_job_type

        retried: list[str] = []
        for failed_job in self._job_service.list_failed_jobs():
            if failed_job.retry_count >= self._job_service.settings.task_max_retries:
                continue
            self._job_service.retry_job(failed_job)
            task = get_task_for_job_type(failed_job.job_type)
            if task is not None:
                async_result = task.delay(str(failed_job.id))
                task_id = str(getattr(async_result, "id", ""))
                if task_id:
                    self._job_service.mark_queued(failed_job, task_id)
                retried.append(str(failed_job.id))
        return {"retried_job_ids": retried, "count": len(retried)}


HANDLER_REGISTRY: dict[str, BaseJobHandler] = {
    ImportNewsHandler.job_type: ImportNewsHandler(),
    SummarizeArticleHandler.job_type: SummarizeArticleHandler(),
    ClassifyArticleHandler.job_type: ClassifyArticleHandler(),
    EpisodePlanningHandler.job_type: EpisodePlanningHandler(),
    GenerateScriptHandler.job_type: GenerateScriptHandler(),
    GenerateAudioHandler.job_type: GenerateAudioHandler(),
    RunAudioPipelineHandler.job_type: RunAudioPipelineHandler(),
    PublishEpisodeHandler.job_type: PublishEpisodeHandler(),
    HealthCheckHandler.job_type: HealthCheckHandler(),
    RetryFailedJobsHandler.job_type: RetryFailedJobsHandler(),
}
