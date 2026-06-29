"""Episode publishing orchestration service."""

import logging
import time
from typing import Any
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.episodes.models import Episode, EpisodeStatus
from apps.publish.models import Platform, PublishedEpisode, PublishJob, PublishJobStatus
from domain.jobs.exceptions import JobPermanentError, JobTransientError
from domain.publish.dtos import PublishEpisodeResult, PublishRequest, PublishResult
from domain.publish.exceptions import (
    PublishError,
    PublisherUnavailableError,
    PublishValidationError,
)
from infrastructure.publish.feed_generator import RSSFeedGenerator
from infrastructure.publish.providers.factory import PublisherFactory
from services.publish.metadata_builder import PublishMetadataBuilder
from services.publish.settings import PublishSettings
from services.publish.validation import PublishValidationService

logger = logging.getLogger(__name__)


class PublishService:
    """Orchestrates episode publishing across configured platforms."""

    def __init__(
        self,
        settings: PublishSettings | None = None,
        validation_service: PublishValidationService | None = None,
        metadata_builder: PublishMetadataBuilder | None = None,
        publisher_factory: PublisherFactory | None = None,
    ) -> None:
        self._settings = settings or PublishSettings.from_django_settings()
        self._validation = validation_service or PublishValidationService(
            self._settings
        )
        self._metadata_builder = metadata_builder or PublishMetadataBuilder(
            self._settings
        )
        self._publisher_factory = publisher_factory or PublisherFactory(self._settings)
        self._feed_generator = RSSFeedGenerator(self._settings)

    def publish_episode(
        self,
        episode_id: UUID | str,
        *,
        platforms: list[str] | tuple[str, ...] | None = None,
    ) -> PublishEpisodeResult:
        """Publish an episode to one or more platforms."""
        started = time.monotonic()
        episode = Episode.objects.get(pk=episode_id)
        target_platforms = self._resolve_platforms(platforms)

        logger.info(
            "Publish started",
            extra={
                "event": "publish_started",
                "episode_id": str(episode.id),
                "platforms": list(target_platforms),
            },
        )

        context = self._validation.build_context(episode)
        metadata = self._metadata_builder.build(context)
        metadata_summary = self._metadata_builder.build_metadata_summary(metadata)

        episode.status = EpisodeStatus.PUBLISHING
        episode.save(update_fields=["status", "updated_at"])

        platform_results: list[PublishResult] = []
        publish_job_ids: list[UUID] = []
        failures: list[str] = []

        for platform in target_platforms:
            publish_job = self._create_publish_job(episode, platform)
            publish_job_ids.append(publish_job.id)
            try:
                result = self._publish_to_platform(
                    episode=episode,
                    platform=platform,
                    context=context,
                    metadata=metadata,
                    publish_job=publish_job,
                )
                platform_results.append(result)
            except PublishValidationError as exc:
                self._mark_publish_failed(publish_job, str(exc))
                failures.append(f"{platform}: {exc}")
            except PublisherUnavailableError as exc:
                self._mark_publish_failed(publish_job, str(exc))
                failures.append(f"{platform}: {exc}")
                raise JobTransientError(str(exc)) from exc
            except PublishError as exc:
                self._mark_publish_failed(publish_job, str(exc))
                failures.append(f"{platform}: {exc}")
                if self._is_transient(exc):
                    raise JobTransientError(str(exc)) from exc
                raise JobPermanentError(str(exc)) from exc

        if failures and len(failures) == len(target_platforms):
            episode.status = EpisodeStatus.FAILED
            episode.save(update_fields=["status", "updated_at"])
            raise JobPermanentError("; ".join(failures))

        if not failures:
            episode.status = EpisodeStatus.COMPLETED
            episode.save(update_fields=["status", "updated_at"])

        elapsed = time.monotonic() - started
        logger.info(
            "Publish completed",
            extra={
                "event": "publish_completed",
                "episode_id": str(episode.id),
                "platforms": list(target_platforms),
                "metadata_summary": metadata_summary,
                "execution_time_seconds": round(elapsed, 3),
                "failures": failures,
            },
        )
        return PublishEpisodeResult(
            episode_id=episode.id,
            platform_results=tuple(platform_results),
            publish_job_ids=tuple(publish_job_ids),
        )

    def publish_ready_episodes(self) -> list[PublishEpisodeResult]:
        """Publish completed episodes with final audio and no publish history."""
        results: list[PublishEpisodeResult] = []
        episodes = Episode.objects.filter(status=EpisodeStatus.COMPLETED).order_by(
            "-publish_date",
            "-created_at",
        )
        for episode in episodes:
            try:
                self._validation.get_final_audio(episode)
            except PublishValidationError:
                continue
            if episode.published_episodes.exists():
                continue
            results.append(self.publish_episode(episode.id))
        return results

    def create_publish_request(
        self,
        episode_id: UUID | str,
        *,
        platforms: list[str] | tuple[str, ...] | None = None,
    ) -> PublishRequest:
        """Build a publish request for API readiness."""
        resolved = self._resolve_platforms(platforms)
        return PublishRequest(
            episode_id=UUID(str(episode_id)),
            platforms=resolved,
        )

    def get_publish_job_status(self, publish_job_id: UUID | str) -> dict[str, Any]:
        """Return publish job status for API readiness."""
        job = PublishJob.objects.select_related("episode").get(pk=publish_job_id)
        return {
            "id": str(job.id),
            "episode_id": str(job.episode_id),
            "platform": job.platform,
            "status": job.status,
            "published_url": job.published_url,
            "external_id": job.external_id,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }

    def retry_publish_job(self, publish_job_id: UUID | str) -> PublishEpisodeResult:
        """Retry a failed publish job."""
        job = PublishJob.objects.select_related("episode").get(pk=publish_job_id)
        if job.status != PublishJobStatus.FAILED:
            raise PublishValidationError(
                f"Publish job {job.id} is not in failed status."
            )
        logger.info(
            "Publish retry started",
            extra={
                "event": "publish_retry_started",
                "publish_job_id": str(job.id),
                "episode_id": str(job.episode_id),
                "platform": job.platform,
                "retry_count": job.episode.publish_jobs.filter(
                    platform=job.platform,
                    status=PublishJobStatus.FAILED,
                ).count(),
            },
        )
        episode = job.episode
        if episode.status == EpisodeStatus.FAILED:
            episode.status = EpisodeStatus.COMPLETED
            episode.save(update_fields=["status", "updated_at"])
        return self.publish_episode(job.episode_id, platforms=[job.platform])

    def cancel_publish_job(self, publish_job_id: UUID | str) -> PublishJob:
        """Cancel a pending publish job."""
        job = PublishJob.objects.get(pk=publish_job_id)
        if job.status not in {PublishJobStatus.PENDING, PublishJobStatus.IN_PROGRESS}:
            raise PublishValidationError(
                f"Publish job {job.id} cannot be cancelled in status '{job.status}'."
            )
        job.status = PublishJobStatus.FAILED
        job.error_message = "Publish job cancelled."
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "status",
                "error_message",
                "completed_at",
                "updated_at",
            ]
        )
        logger.info(
            "Publish job cancelled",
            extra={
                "event": "publish_job_cancelled",
                "publish_job_id": str(job.id),
            },
        )
        return job

    def _publish_to_platform(
        self,
        *,
        episode: Episode,
        platform: str,
        context: Any,
        metadata: Any,
        publish_job: PublishJob,
    ) -> PublishResult:
        self._validation.validate_for_platform(context, platform)
        publisher = self._publisher_factory.create(platform)

        if not publisher.health_check():
            raise PublisherUnavailableError(
                f"Publisher for platform '{platform}' is unavailable."
            )

        self._mark_publish_running(publish_job)
        logger.info(
            "Publishing to platform",
            extra={
                "event": "publish_platform_started",
                "episode_id": str(episode.id),
                "platform": platform,
                "publish_job_id": str(publish_job.id),
            },
        )

        result = publisher.publish(context, metadata)
        self._mark_publish_succeeded(publish_job, result)
        self._create_published_episode(episode, result, metadata)
        if platform == Platform.RSS:
            feed_path = self._feed_generator.write_feed()
            logger.info(
                "RSS feed regenerated",
                extra={
                    "event": "rss_feed_regenerated",
                    "episode_id": str(episode.id),
                    "feed_path": str(feed_path),
                },
            )

        logger.info(
            "Publish succeeded",
            extra={
                "event": "publish_succeeded",
                "episode_id": str(episode.id),
                "platform": platform,
                "published_url": result.published_url,
                "external_id": result.external_id,
                "publish_job_id": str(publish_job.id),
            },
        )
        return result

    @transaction.atomic
    def _create_publish_job(self, episode: Episode, platform: str) -> PublishJob:
        self._validation.validate_platform(platform)
        return PublishJob.objects.create(
            episode=episode,
            platform=platform,
            status=PublishJobStatus.PENDING,
        )

    def _mark_publish_running(self, publish_job: PublishJob) -> None:
        publish_job.status = PublishJobStatus.IN_PROGRESS
        publish_job.started_at = timezone.now()
        publish_job.error_message = ""
        publish_job.save(
            update_fields=["status", "started_at", "error_message", "updated_at"]
        )

    def _mark_publish_succeeded(
        self,
        publish_job: PublishJob,
        result: PublishResult,
    ) -> None:
        publish_job.status = PublishJobStatus.COMPLETED
        publish_job.published_url = result.published_url
        publish_job.external_id = result.external_id
        publish_job.completed_at = timezone.now()
        publish_job.error_message = ""
        publish_job.save(
            update_fields=[
                "status",
                "published_url",
                "external_id",
                "completed_at",
                "error_message",
                "updated_at",
            ]
        )

    def _mark_publish_failed(self, publish_job: PublishJob, message: str) -> None:
        publish_job.status = PublishJobStatus.FAILED
        publish_job.error_message = message
        publish_job.completed_at = timezone.now()
        publish_job.save(
            update_fields=["status", "error_message", "completed_at", "updated_at"]
        )
        logger.error(
            "Publish failed",
            extra={
                "event": "publish_failed",
                "publish_job_id": str(publish_job.id),
                "episode_id": str(publish_job.episode_id),
                "platform": publish_job.platform,
                "error_message": message,
            },
        )

    def _create_published_episode(
        self,
        episode: Episode,
        result: PublishResult,
        metadata: Any,
    ) -> PublishedEpisode:
        stored_metadata = dict(result.metadata)
        return PublishedEpisode.objects.create(
            episode=episode,
            platform=result.platform,
            published_url=result.published_url,
            external_id=result.external_id,
            published_at=timezone.now(),
            metadata=stored_metadata,
        )

    def _resolve_platforms(
        self,
        platforms: list[str] | tuple[str, ...] | None,
    ) -> tuple[str, ...]:
        resolved = tuple(platforms) if platforms else self._settings.enabled_platforms()
        if not resolved:
            raise PublishValidationError("No publishing platforms are enabled.")
        return resolved

    def _is_transient(self, exc: PublishError) -> bool:
        return isinstance(exc, PublisherUnavailableError)
