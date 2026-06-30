"""High-level admin operations delegating to domain services."""

import json
from typing import Any

from django.db.models import QuerySet

from apps.articles.models import Article
from apps.audio.models import AudioAsset
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import NewsSource
from apps.scripts.models import Script
from domain.publish.exceptions import PublishValidationError
from services.admin.action_logger import AdminActionLogger
from services.admin.dispatch import AdminJobDispatchService
from services.intelligence.scoring_service import ArticleScoreService
from services.llm.service import LLMService
from services.publish.service import PublishService


class AdminOperationsService:
    """Coordinates admin-triggered operations through domain services."""

    def __init__(
        self,
        dispatch: AdminJobDispatchService | None = None,
        publish_service: PublishService | None = None,
    ) -> None:
        self._dispatch = dispatch or AdminJobDispatchService()
        self._publish = publish_service or PublishService()
        self._logger = AdminActionLogger()

    def log_action(
        self,
        *,
        request_user_id: int | None,
        action: str,
        resource_type: str,
        resource_ids: list[str],
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._logger.log(
            action=action,
            user_id=request_user_id,
            resource_type=resource_type,
            resource_ids=resource_ids,
            extra=extra,
        )

    def import_sources(
        self,
        sources: QuerySet[NewsSource],
        *,
        user_id: int | None,
    ) -> list[str]:
        job_ids: list[str] = []
        for source in sources:
            job = self._dispatch.import_news(source_id=str(source.id))
            job_ids.append(str(job.id))
        self.log_action(
            request_user_id=user_id,
            action="manual_import",
            resource_type="news_source",
            resource_ids=[str(s.id) for s in sources],
            extra={"job_ids": job_ids},
        )
        return job_ids

    def health_check_sources(
        self,
        sources: QuerySet[NewsSource],
        *,
        user_id: int | None,
    ) -> list[str]:
        job_ids: list[str] = []
        for source in sources:
            job = self._dispatch.health_check(
                source_id=str(source.id),
                provider_type=source.provider_type,
            )
            job_ids.append(str(job.id))
        self.log_action(
            request_user_id=user_id,
            action="health_check",
            resource_type="news_source",
            resource_ids=[str(s.id) for s in sources],
        )
        return job_ids

    def rescore_articles(
        self,
        articles: QuerySet[Article],
        *,
        user_id: int | None,
    ) -> int:
        service = ArticleScoreService(LLMService())
        count = 0
        for article in articles:
            service.score(article)
            count += 1
        self.log_action(
            request_user_id=user_id,
            action="re_score",
            resource_type="article",
            resource_ids=[str(a.id) for a in articles],
        )
        return count

    def add_articles_to_draft_episode(
        self,
        articles: QuerySet[Article],
        *,
        user_id: int | None,
    ) -> str | None:
        episode = (
            Episode.objects.filter(
                status__in=[EpisodeStatus.DRAFT, EpisodeStatus.COLLECTING]
            )
            .order_by("-created_at")
            .first()
        )
        if episode is None:
            return None
        for article in articles:
            EpisodeArticle.objects.get_or_create(episode=episode, article=article)
        self.log_action(
            request_user_id=user_id,
            action="add_to_episode",
            resource_type="article",
            resource_ids=[str(a.id) for a in articles],
            extra={"episode_id": str(episode.id)},
        )
        return str(episode.id)

    def export_script_json(self, script: Script) -> str:
        segments = [
            {
                "sequence": segment.sequence,
                "speaker": segment.speaker,
                "voice": segment.voice,
                "emotion": segment.emotion,
                "text": segment.text,
            }
            for segment in script.segments.order_by("sequence")
        ]
        payload = {
            "id": str(script.id),
            "episode_id": str(script.episode_id),
            "version": script.version,
            "title": script.title,
            "status": script.status,
            "segments": segments,
        }
        return json.dumps(payload, indent=2)

    def delete_audio_assets(
        self,
        assets: QuerySet[AudioAsset],
        *,
        user_id: int | None,
    ) -> int:
        count = assets.count()
        asset_ids = [str(a.id) for a in assets]
        assets.delete()
        self.log_action(
            request_user_id=user_id,
            action="delete_audio",
            resource_type="audio_asset",
            resource_ids=asset_ids,
        )
        return count

    def retry_publish_jobs(
        self,
        publish_job_ids: list[str],
        *,
        user_id: int | None,
    ) -> list[str]:
        retried: list[str] = []
        for job_id in publish_job_ids:
            try:
                self._publish.retry_publish_job(job_id)
                retried.append(job_id)
            except PublishValidationError:
                continue
        self.log_action(
            request_user_id=user_id,
            action="retry_publish",
            resource_type="publish_job",
            resource_ids=retried,
        )
        return retried

    def cancel_publish_jobs(
        self,
        publish_job_ids: list[str],
        *,
        user_id: int | None,
    ) -> int:
        cancelled = 0
        for job_id in publish_job_ids:
            try:
                self._publish.cancel_publish_job(job_id)
                cancelled += 1
            except PublishValidationError:
                continue
        self.log_action(
            request_user_id=user_id,
            action="cancel_publish",
            resource_type="publish_job",
            resource_ids=publish_job_ids,
        )
        return cancelled
