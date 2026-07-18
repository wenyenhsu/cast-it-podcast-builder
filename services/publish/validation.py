"""Pre-publish validation for episodes."""

import mimetypes
from pathlib import Path

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode, EpisodeStatus
from apps.publish.models import Platform
from domain.publish.dtos import EpisodePublishContext
from domain.publish.exceptions import PublishValidationError
from services.publish.settings import PublishSettings


class PublishValidationService:
    """Validates episode readiness before publishing."""

    _READY_STATUSES = {EpisodeStatus.COMPLETED, EpisodeStatus.PUBLISHING}
    _MIME_BY_FORMAT = {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "m4a": "audio/mp4",
        "aac": "audio/aac",
    }

    def __init__(self, settings: PublishSettings | None = None) -> None:
        self._settings = settings or PublishSettings.from_django_settings()

    def validate_episode(self, episode: Episode) -> None:
        """Validate that an episode is ready to publish."""
        if episode.status not in self._READY_STATUSES:
            raise PublishValidationError(
                f"Episode {episode.id} status must be completed or publishing, "
                f"got '{episode.status}'."
            )
        if not episode.title.strip():
            raise PublishValidationError("Episode title is required for publishing.")
        has_linked_articles = episode.articles.exists()
        has_active_manual_script = episode.scripts.filter(
            llm_provider="manual",
            metadata__is_active=True,
        ).exists()
        if not has_linked_articles and not has_active_manual_script:
            raise PublishValidationError(
                "Episode must include at least one article or an active manual script "
                "before publishing."
            )
        if episode.duration_seconds is None or episode.duration_seconds <= 0:
            raise PublishValidationError(
                "Episode duration must be a positive number of seconds."
            )

    def validate_platform(self, platform: str) -> None:
        """Validate that a platform is supported and enabled."""
        valid_values = {choice.value for choice in Platform}
        if platform not in valid_values:
            raise PublishValidationError(
                f"Unsupported publishing platform: {platform}."
            )

        if platform == Platform.RSS and not self._settings.enable_rss_publishing:
            raise PublishValidationError("RSS publishing is disabled.")
        if (
            platform == Platform.YOUTUBE
            and not self._settings.enable_youtube_publishing
        ):
            raise PublishValidationError("YouTube publishing is disabled.")

    def get_final_audio(self, episode: Episode) -> AudioAsset:
        """Return the final episode audio asset."""
        audio = (
            AudioAsset.objects.filter(
                episode=episode,
                is_final_episode_audio=True,
                status=AudioAssetStatus.READY,
            )
            .order_by("-created_at")
            .first()
        )
        if audio is None:
            raise PublishValidationError(
                f"Episode {episode.id} has no ready final audio asset."
            )
        return audio

    def build_context(self, episode: Episode) -> EpisodePublishContext:
        """Validate episode and build publish context."""
        self.validate_episode(episode)
        audio = self.get_final_audio(episode)
        audio_path = self._resolve_audio_path(audio.file_path)
        if not audio_path.exists():
            raise PublishValidationError(
                f"Final audio file does not exist: {audio_path}"
            )

        duration = episode.duration_seconds or audio.duration or 0
        if duration <= 0:
            raise PublishValidationError("Audio duration must be greater than zero.")

        audio_format = audio.format or audio_path.suffix.lstrip(".") or "mp3"
        mime_type = self._MIME_BY_FORMAT.get(
            audio_format.lower(),
            mimetypes.guess_type(str(audio_path))[0] or "audio/mpeg",
        )
        audio_url = self._build_audio_url(audio.file_path)

        publish_date = episode.publish_date
        if publish_date is not None:
            from datetime import datetime

            from django.utils import timezone

            publish_dt = datetime.combine(
                publish_date,
                datetime.min.time(),
                tzinfo=timezone.get_current_timezone(),
            )
        else:
            publish_dt = None

        return EpisodePublishContext(
            episode_id=episode.id,
            title=episode.title,
            description=episode.description,
            summary=episode.summary,
            language=episode.language,
            duration_seconds=int(duration),
            publish_date=publish_dt,
            cover_image=episode.cover_image,
            audio_file_path=audio_path,
            audio_url=audio_url,
            audio_format=audio_format,
            audio_file_size=audio.file_size,
            audio_mime_type=mime_type,
        )

    def validate_for_platform(
        self,
        context: EpisodePublishContext,
        platform: str,
    ) -> None:
        """Validate platform-specific requirements."""
        self.validate_platform(platform)
        if platform == Platform.YOUTUBE and not context.audio_file_path.exists():
            raise PublishValidationError(
                "YouTube publishing requires a local audio file."
            )

    def _resolve_audio_path(self, file_path: str) -> Path:
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self._settings.media_root / path

    def _build_audio_url(self, file_path: str) -> str:
        relative = file_path.lstrip("/")
        if relative.startswith("media/"):
            relative = relative[len("media/") :]
        base = self._settings.rss_feed_audio_base_url.rstrip("/")
        return f"{base}/{relative}"
