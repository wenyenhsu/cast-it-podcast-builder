"""Publishes finished episodes to Supabase for the public listener frontend."""

import logging
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from django.conf import settings as django_settings
from django.utils.text import slugify

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode
from domain.intelligence.constants import ALLOWED_TAGS

TAXONOMY_SLUGS = {slugify(tag) for tag in ALLOWED_TAGS}

logger = logging.getLogger(__name__)


class HTTPClientProtocol(Protocol):
    """Protocol for HTTP clients used by SupabasePublisher."""

    def post(self, url: str, **kwargs: Any) -> Any: ...

    def delete(self, url: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class SupabaseSettings:
    """Supabase connection configuration loaded from environment variables."""

    url: str
    service_role_key: str
    audio_bucket: str

    @classmethod
    def from_django_settings(cls) -> "SupabaseSettings":
        return cls(
            url=getattr(django_settings, "SUPABASE_URL", "").rstrip("/"),
            service_role_key=getattr(
                django_settings, "SUPABASE_SERVICE_ROLE_KEY", ""
            ),
            audio_bucket=getattr(
                django_settings, "SUPABASE_AUDIO_BUCKET", "episode-audio"
            ),
        )

    def validate(self) -> None:
        if not self.url or not self.service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set."
            )


@dataclass(frozen=True)
class PublishResult:
    """Outcome of publishing one episode to Supabase."""

    episode_id: str
    audio_url: str


class SupabasePublisher:
    """Uploads final episode audio and upserts episode metadata."""

    def __init__(
        self,
        settings: SupabaseSettings | None = None,
        http_client: HTTPClientProtocol | None = None,
    ) -> None:
        self._settings = settings or SupabaseSettings.from_django_settings()
        self._settings.validate()
        if http_client is None:
            import httpx

            http_client = httpx.Client(timeout=120.0)
        self._http = http_client

    def _headers(self, **extra: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.service_role_key}",
            "apikey": self._settings.service_role_key,
            **extra,
        }

    def sync_taxonomy(self) -> int:
        """Upsert ALLOWED_TAGS into Supabase so the taxonomy never drifts.

        Upsert-only: tags removed from the code list are kept in Supabase
        because published episodes may still reference them.
        """
        rows = [{"slug": slugify(tag), "name": tag} for tag in ALLOWED_TAGS]
        response = self._http.post(
            f"{self._settings.url}/rest/v1/tags?on_conflict=slug",
            headers=self._headers(
                **{
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                }
            ),
            json=rows,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Tag taxonomy sync failed ({response.status_code}): {response.text}"
            )
        return len(rows)

    def final_audio_asset(self, episode: Episode) -> AudioAsset | None:
        return (
            AudioAsset.objects.filter(
                episode=episode,
                is_final_episode_audio=True,
                status=AudioAssetStatus.READY,
            )
            .exclude(file_path="")
            .order_by("-generated_at")
            .first()
        )

    def publishable_episodes(self) -> list[Episode]:
        episode_ids = (
            AudioAsset.objects.filter(
                is_final_episode_audio=True,
                status=AudioAssetStatus.READY,
            )
            .exclude(file_path="")
            .values_list("episode_id", flat=True)
            .distinct()
        )
        return list(Episode.objects.filter(id__in=episode_ids))

    def publish_episode(self, episode: Episode) -> PublishResult:
        asset = self.final_audio_asset(episode)
        if asset is None:
            raise ValueError(f"Episode {episode.id} has no final ready audio.")

        audio_url = self._upload_audio(asset)
        self._upsert_episode(episode, asset, audio_url)
        self._replace_episode_tags(episode)

        logger.info(
            "Episode published to Supabase",
            extra={
                "event": "supabase_episode_published",
                "episode_id": str(episode.id),
                "audio_url": audio_url,
            },
        )
        return PublishResult(episode_id=str(episode.id), audio_url=audio_url)

    def _upload_audio(self, asset: AudioAsset) -> str:
        local_path = Path(django_settings.MEDIA_ROOT) / asset.file_path
        if not local_path.exists():
            raise FileNotFoundError(f"Audio file missing: {local_path}")

        object_path = asset.file_path
        bucket = self._settings.audio_bucket
        content_type = f"audio/{asset.format or 'mpeg'}"
        response = self._http.post(
            f"{self._settings.url}/storage/v1/object/{bucket}/{object_path}",
            headers=self._headers(
                **{"Content-Type": content_type, "x-upsert": "true"}
            ),
            content=local_path.read_bytes(),
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Audio upload failed ({response.status_code}): {response.text}"
            )
        return (
            f"{self._settings.url}/storage/v1/object/public/{bucket}/{object_path}"
        )

    def _top_tags(self, episode: Episode, limit: int = 3) -> list[dict[str, str]]:
        """Most common taxonomy tags across the episode's articles."""
        counts = Counter()
        names: dict[str, str] = {}
        for article in episode.articles.prefetch_related("tags"):
            for tag in article.tags.all():
                # Skip legacy free-form tags that predate the taxonomy;
                # Supabase only knows taxonomy slugs.
                if tag.slug not in TAXONOMY_SLUGS:
                    continue
                counts[tag.slug] += 1
                names[tag.slug] = tag.name
        return [
            {"slug": slug, "name": names[slug]}
            for slug, _ in counts.most_common(limit)
        ]

    def _replace_episode_tags(self, episode: Episode) -> None:
        tags = self._top_tags(episode)
        delete = self._http.delete(
            f"{self._settings.url}/rest/v1/episode_tags?episode_id=eq.{episode.id}",
            headers=self._headers(),
        )
        if delete.status_code >= 400:
            raise RuntimeError(
                f"Episode tag cleanup failed ({delete.status_code}): {delete.text}"
            )
        if not tags:
            return
        response = self._http.post(
            f"{self._settings.url}/rest/v1/episode_tags",
            headers=self._headers(
                **{
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates,return=minimal",
                }
            ),
            json=[
                {"episode_id": str(episode.id), "tag_slug": tag["slug"]}
                for tag in tags
            ],
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Episode tag upsert failed ({response.status_code}): {response.text}"
            )

    def _primary_category(self, episode: Episode) -> str:
        categories = Counter(
            episode.articles.exclude(category="").values_list(
                "category", flat=True
            )
        )
        if not categories:
            return ""
        return categories.most_common(1)[0][0]

    def _upsert_episode(
        self,
        episode: Episode,
        asset: AudioAsset,
        audio_url: str,
    ) -> None:
        row = {
            "id": str(episode.id),
            "title": episode.title,
            "description": episode.description,
            "summary": episode.summary,
            "language": episode.language,
            "publish_date": (
                episode.publish_date.isoformat() if episode.publish_date else None
            ),
            "duration_seconds": episode.duration_seconds or asset.duration,
            "audio_url": audio_url,
            "cover_url": episode.cover_image or None,
            "category": self._primary_category(episode),
        }
        response = self._http.post(
            f"{self._settings.url}/rest/v1/episodes?on_conflict=id",
            headers=self._headers(
                **{
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                }
            ),
            json=[row],
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"Episode upsert failed ({response.status_code}): {response.text}"
            )
