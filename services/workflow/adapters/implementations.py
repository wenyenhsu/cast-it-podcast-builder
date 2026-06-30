"""Workflow step adapter implementations."""

from datetime import timedelta
from typing import Any, Protocol

from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode
from apps.workflow.models import WorkflowStepRun
from domain.workflow.dtos import StepExecutionResult
from domain.workflow.enums import WorkflowStepType
from domain.workflow.exceptions import WorkflowStepError
from services.workflow.adapters.base import WorkflowStepAdapter


class CollectArticlesPort(Protocol):
    def collect(self, *, source_id: str | None) -> dict[str, Any]: ...


class ArticleProcessingPort(Protocol):
    def summarize(self, *, language: str) -> dict[str, Any]: ...

    def classify(self, *, language: str) -> dict[str, Any]: ...

    def rank(self, *, language: str) -> dict[str, Any]: ...


class EpisodePlanningPort(Protocol):
    def plan(self, *, language: str) -> dict[str, Any]: ...


class ScriptGenerationPort(Protocol):
    def generate(self, *, episode_id: str) -> dict[str, Any]: ...


class AudioGenerationPort(Protocol):
    def generate(self, *, episode_id: str, script_id: str | None) -> dict[str, Any]: ...


class AudioPipelinePort(Protocol):
    def process(self, *, episode_id: str) -> dict[str, Any]: ...


class PublishPort(Protocol):
    def publish(
        self,
        *,
        episode_id: str,
        platforms: list[str] | None,
    ) -> dict[str, Any]: ...


class KnowledgeIndexPort(Protocol):
    def index_recent(self) -> dict[str, Any]: ...


def _load_todays_articles(language: str = "en") -> list[Article]:
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    return list(
        Article.objects.filter(
            status__in=[ArticleStatus.COLLECTED, ArticleStatus.PROCESSED],
            language=language,
            published_at__gte=today_start,
            published_at__lt=tomorrow_start,
        ).order_by("-published_at")
    )


class DefaultCollectArticlesAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.COLLECT_ARTICLES

    def __init__(self, port: CollectArticlesPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if self._port is not None:
            output = self._port.collect(source_id=context.get("source_id"))
            return StepExecutionResult(output=output)

        from apps.providers.models import NewsSource
        from services.news.import_service import NewsImportService
        from services.news.provider_factory import ProviderFactory

        service = NewsImportService()
        factory = ProviderFactory()
        source_id = context.get("source_id")
        if source_id:
            sources = [NewsSource.objects.get(pk=source_id)]
        else:
            sources = list(NewsSource.objects.filter(enabled=True))

        total_imported = 0
        for source in sources:
            provider = factory.create(source)
            result = service.import_from_provider(provider)
            total_imported += result.imported
        return StepExecutionResult(output={"imported_count": total_imported})


class DefaultSummarizeArticlesAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.SUMMARIZE_ARTICLES

    def __init__(self, port: ArticleProcessingPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        language = str(context.get("language", "en"))
        if self._port is not None:
            return StepExecutionResult(output=self._port.summarize(language=language))

        from services.intelligence.summary_service import ArticleSummaryService
        from services.llm.service import LLMService

        service = ArticleSummaryService(LLMService())
        count = 0
        for article in _load_todays_articles(language):
            if service.summarize(article):
                count += 1
        return StepExecutionResult(output={"articles_summarized": count})


class DefaultClassifyArticlesAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.CLASSIFY_ARTICLES

    def __init__(self, port: ArticleProcessingPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        language = str(context.get("language", "en"))
        if self._port is not None:
            return StepExecutionResult(output=self._port.classify(language=language))

        from services.intelligence.classification_service import (
            ArticleClassificationService,
        )
        from services.llm.service import LLMService

        service = ArticleClassificationService(LLMService())
        count = 0
        for article in _load_todays_articles(language):
            service.classify(article)
            count += 1
        return StepExecutionResult(output={"articles_classified": count})


class DefaultRankArticlesAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.RANK_ARTICLES

    def __init__(self, port: ArticleProcessingPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        language = str(context.get("language", "en"))
        if self._port is not None:
            return StepExecutionResult(output=self._port.rank(language=language))

        from services.intelligence.ranking_service import ArticleRankingService
        from services.intelligence.topic_cluster_service import TopicClusteringService

        articles = _load_todays_articles(language)
        clusters = TopicClusteringService().cluster_articles(articles)
        ranked = ArticleRankingService().rank(articles, clusters)
        return StepExecutionResult(
            output={
                "ranked_article_ids": [str(item.article_id) for item in ranked],
                "cluster_count": len(clusters),
            }
        )


class DefaultPlanEpisodeAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.PLAN_EPISODE

    def __init__(self, port: EpisodePlanningPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        language = str(context.get("language", "en"))
        if self._port is not None:
            return StepExecutionResult(output=self._port.plan(language=language))

        from services.intelligence.pipeline import EpisodePlanningPipeline
        from services.llm.service import LLMService

        result = EpisodePlanningPipeline(LLMService()).run(language=language)
        episode_id = None
        if result.episode_plan is not None:
            episode_id = str(result.episode_plan.episode_id)
        output = {
            "episode_id": episode_id,
            "articles_processed": result.articles_processed,
        }
        return StepExecutionResult(output=output)


class DefaultGenerateScriptAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.GENERATE_SCRIPT

    def __init__(self, port: ScriptGenerationPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        episode_id = context.get("episode_id") or step_run.input_data.get("episode_id")
        if not episode_id:
            raise WorkflowStepError("episode_id is required for script generation.")

        if self._port is not None:
            output = self._port.generate(episode_id=str(episode_id))
            return StepExecutionResult(output=output)

        from services.llm.service import LLMService
        from services.scripts.generation_service import ScriptGenerationService

        episode = Episode.objects.get(pk=episode_id)
        script = ScriptGenerationService(LLMService()).generate(episode)
        return StepExecutionResult(
            output={"script_id": str(script.id), "episode_id": str(episode_id)},
        )


class DefaultGenerateAudioAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.GENERATE_AUDIO

    def __init__(self, port: AudioGenerationPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        episode_id = context.get("episode_id")
        script_id = context.get("script_id")
        if self._port is not None:
            return StepExecutionResult(
                output=self._port.generate(
                    episode_id=str(episode_id),
                    script_id=str(script_id) if script_id else None,
                )
            )

        from apps.scripts.models import Script
        from services.audio.generation_service import AudioGenerationService
        from services.scripts.version_service import ScriptVersionService

        if not script_id and episode_id:
            script = ScriptVersionService().get_active_script(episode_id)
            if script:
                script_id = str(script.id)
        if not script_id:
            raise WorkflowStepError("script_id is required for audio generation.")

        script = Script.objects.select_related("episode").get(pk=script_id)
        results = AudioGenerationService().generate_for_script(script)
        return StepExecutionResult(
            output={
                "script_id": str(script_id),
                "episode_id": str(script.episode_id),
                "segment_count": len(results),
            }
        )


class DefaultProcessAudioAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.PROCESS_AUDIO

    def __init__(self, port: AudioPipelinePort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        episode_id = self._require_key(context, "episode_id")
        if self._port is not None:
            output = self._port.process(episode_id=str(episode_id))
            return StepExecutionResult(output=output)

        from services.audio.pipeline.service import AudioPipelineService

        episode = Episode.objects.get(pk=episode_id)
        result = AudioPipelineService().process_episode(episode)
        return StepExecutionResult(
            output={
                "episode_id": str(episode_id),
                "output_path": result.output_path,
                "duration_seconds": result.duration_seconds,
            }
        )


class DefaultPublishEpisodeAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.PUBLISH_EPISODE

    def __init__(self, port: PublishPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        episode_id = self._require_key(context, "episode_id")
        platforms = context.get("platforms")
        if self._port is not None:
            platform_list = platforms if isinstance(platforms, list) else None
            return StepExecutionResult(
                output=self._port.publish(
                    episode_id=str(episode_id),
                    platforms=platform_list,
                )
            )

        from services.publish.service import PublishService

        result = PublishService().publish_episode(
            episode_id,
            platforms=platforms,
        )
        return StepExecutionResult(
            output={
                "episode_id": str(result.episode_id),
                "platforms": [item.platform for item in result.platform_results],
            }
        )


class DefaultIndexKnowledgeAdapter(WorkflowStepAdapter):
    step_type = WorkflowStepType.INDEX_KNOWLEDGE

    def __init__(self, port: KnowledgeIndexPort | None = None) -> None:
        self._port = port

    def execute(
        self,
        *,
        step_run: WorkflowStepRun,
        context: dict[str, Any],
    ) -> StepExecutionResult:
        if self._port is not None:
            return StepExecutionResult(output=self._port.index_recent())

        from services.knowledge.indexing import IndexingService
        from services.knowledge.normalizer import DocumentNormalizer

        normalizer = DocumentNormalizer()
        indexing = IndexingService()
        indexed = 0
        for article in _load_todays_articles(str(context.get("language", "en"))):
            request = normalizer.from_article(article)
            indexing.index_document(request)
            indexed += 1
        return StepExecutionResult(output={"documents_indexed": indexed})
