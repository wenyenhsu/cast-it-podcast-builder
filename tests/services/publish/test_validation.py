"""Tests for publish validation."""

from pathlib import Path

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from domain.publish.exceptions import PublishValidationError
from services.publish.settings import PublishSettings
from services.publish.validation import PublishValidationService


def test_validate_episode_requires_completed_status(
    publishable_episode: Episode,
    publish_settings: PublishSettings,
) -> None:
    service = PublishValidationService(publish_settings)
    publishable_episode.status = EpisodeStatus.DRAFT
    publishable_episode.save(update_fields=["status"])
    with pytest.raises(PublishValidationError, match="status must be completed"):
        service.validate_episode(publishable_episode)


def test_validate_platform_disabled(
    publish_settings: PublishSettings,
) -> None:
    disabled = PublishSettings(
        **{
            **publish_settings.__dict__,
            "enable_rss_publishing": False,
        }
    )
    service = PublishValidationService(disabled)
    with pytest.raises(PublishValidationError, match="RSS publishing is disabled"):
        service.validate_platform("rss")


def test_build_context_success(
    publishable_episode: Episode,
    publish_settings: PublishSettings,
    tmp_path: Path,
) -> None:
    del tmp_path
    service = PublishValidationService(publish_settings)
    context = service.build_context(publishable_episode)
    assert context.title == publishable_episode.title
    assert context.duration_seconds == 600
    assert context.audio_url.startswith("https://podcast.test/media/")


def test_build_context_missing_audio(
    publishable_episode: Episode,
    publish_settings: PublishSettings,
) -> None:
    publishable_episode.audio_assets.all().delete()
    service = PublishValidationService(publish_settings)
    with pytest.raises(PublishValidationError, match="no ready final audio"):
        service.build_context(publishable_episode)
