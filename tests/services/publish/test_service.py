"""Tests for PublishService."""

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.publish.models import Platform, PublishedEpisode, PublishJobStatus
from domain.jobs.exceptions import JobPermanentError
from domain.publish.dtos import PublishResult
from domain.publish.exceptions import PublishValidationError
from infrastructure.publish.providers.base import BasePublisher
from infrastructure.publish.providers.factory import PublisherFactory
from infrastructure.publish.providers.youtube.client import StubYouTubeAPIClient
from infrastructure.publish.providers.youtube.publisher import YouTubePublisher
from services.publish.service import PublishService


class StubPublisher(BasePublisher):
    def __init__(self, platform: str, *, fail: bool = False) -> None:
        self.platform_name = platform
        self._fail = fail
        self.calls: list[str] = []

    @property
    def platform(self) -> str:
        return self.platform_name

    @classmethod
    def supported_platforms(cls) -> tuple[str, ...]:
        return ("stub",)

    def publish(self, context, metadata) -> PublishResult:
        self.calls.append("publish")
        if self._fail:
            raise PublishValidationError("Stub publish failure.")
        return PublishResult(
            platform=self.platform_name,
            published_url=f"https://example.com/{self.platform_name}",
            external_id=f"ext-{self.platform_name}",
        )

    def validate(self, context, metadata) -> None:
        self.calls.append("validate")

    def health_check(self) -> bool:
        return True

    def build_metadata(self, context):
        raise NotImplementedError


def test_publish_episode_rss_only(
    publishable_episode: Episode,
    publish_settings,
) -> None:
    rss_only = publish_settings.__class__(
        **{**publish_settings.__dict__, "enable_youtube_publishing": False}
    )
    service = PublishService(settings=rss_only)
    result = service.publish_episode(publishable_episode.id, platforms=["rss"])

    publishable_episode.refresh_from_db()
    assert publishable_episode.status == EpisodeStatus.COMPLETED
    assert publishable_episode.publish == 1
    assert len(result.platform_results) == 1
    assert result.platform_results[0].platform == "rss"
    assert PublishedEpisode.objects.filter(episode=publishable_episode).count() == 1
    assert rss_only.resolve_feed_output_path().exists()


def test_publish_episode_youtube_and_rss(
    publishable_episode: Episode,
    publish_settings,
) -> None:
    youtube = YouTubePublisher(
        settings=publish_settings,
        client=StubYouTubeAPIClient(),
    )
    factory = PublisherFactory(
        publish_settings,
        publishers={
            Platform.RSS: factory_rss_publisher(publish_settings),
            Platform.YOUTUBE: youtube,
        },
    )
    service = PublishService(settings=publish_settings, publisher_factory=factory)
    result = service.publish_episode(
        publishable_episode.id,
        platforms=["rss", "youtube"],
    )
    assert len(result.platform_results) == 2
    assert PublishedEpisode.objects.filter(episode=publishable_episode).count() == 2


def factory_rss_publisher(publish_settings):
    from infrastructure.publish.providers.rss.publisher import RSSPublisher

    return RSSPublisher(publish_settings)


def test_publish_job_lifecycle(
    publishable_episode: Episode,
    publish_settings,
) -> None:
    service = PublishService(settings=publish_settings)
    result = service.publish_episode(publishable_episode.id, platforms=["rss"])
    job_status = service.get_publish_job_status(result.publish_job_ids[0])
    assert job_status["status"] == PublishJobStatus.COMPLETED
    assert job_status["published_url"]


def test_retry_publish_job(
    publishable_episode: Episode,
    publish_settings,
) -> None:
    failing = StubPublisher("rss", fail=True)
    factory = PublisherFactory(
        publish_settings,
        publishers={Platform.RSS: failing},
    )
    service = PublishService(settings=publish_settings, publisher_factory=factory)
    with pytest.raises(JobPermanentError):
        service.publish_episode(publishable_episode.id, platforms=["rss"])

    failed_job = publishable_episode.publish_jobs.get(platform="rss")
    assert failed_job.status == PublishJobStatus.FAILED

    working_factory = PublisherFactory(
        publish_settings,
        publishers={Platform.RSS: StubPublisher("rss")},
    )
    retry_service = PublishService(
        settings=publish_settings,
        publisher_factory=working_factory,
    )
    retry_service.retry_publish_job(failed_job.id)
    failed_job.refresh_from_db()
    assert failed_job.status == PublishJobStatus.FAILED
    assert publishable_episode.publish_jobs.filter(
        platform="rss",
        status=PublishJobStatus.COMPLETED,
    ).exists()


def test_cancel_publish_job(
    publishable_episode: Episode,
    publish_settings,
) -> None:
    from apps.publish.models import PublishJob

    job = PublishJob.objects.create(
        episode=publishable_episode,
        platform=Platform.RSS,
        status=PublishJobStatus.PENDING,
    )
    service = PublishService(settings=publish_settings)
    cancelled = service.cancel_publish_job(job.id)
    assert cancelled.status == PublishJobStatus.FAILED
    assert "cancelled" in cancelled.error_message.lower()


def test_publish_validation_error_when_no_platforms(
    publishable_episode: Episode,
    publish_settings,
) -> None:
    disabled = publish_settings.__class__(
        **{
            **publish_settings.__dict__,
            "enable_rss_publishing": False,
            "enable_youtube_publishing": False,
        }
    )
    service = PublishService(settings=disabled)
    with pytest.raises(PublishValidationError, match="No publishing platforms"):
        service.publish_episode(publishable_episode.id)
