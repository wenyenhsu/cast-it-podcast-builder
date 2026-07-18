"""Tests for publish validation."""

from pathlib import Path

import pytest

from apps.episodes.models import Episode, EpisodeStatus
from apps.scripts.models import Script, ScriptMetadata, ScriptStatus, ValidationStatus
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


def test_validate_episode_requires_article_or_manual_script(
    publishable_episode: Episode,
    publish_settings: PublishSettings,
) -> None:
    publishable_episode.episode_articles.all().delete()
    service = PublishValidationService(publish_settings)

    with pytest.raises(PublishValidationError, match="at least one article"):
        service.validate_episode(publishable_episode)


def test_validate_episode_allows_active_manual_script_without_article(
    publishable_episode: Episode,
    publish_settings: PublishSettings,
) -> None:
    publishable_episode.episode_articles.all().delete()
    script = Script.objects.create(
        episode=publishable_episode,
        version=1,
        llm_provider="manual",
        prompt_version="manual",
        status=ScriptStatus.READY,
        validation_status=ValidationStatus.PASSED,
    )
    ScriptMetadata.objects.create(script=script, is_active=True)

    PublishValidationService(publish_settings).validate_episode(publishable_episode)


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
