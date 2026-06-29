"""Build reusable publishing metadata for episodes."""

import re
import unicodedata
from datetime import datetime
from typing import Any
from uuid import UUID

from django.utils import timezone

from domain.publish.dtos import (
    EnclosureMetadata,
    EpisodePublishContext,
    PublishMetadata,
    RSSItemFields,
    YouTubeMetadataFields,
)
from domain.publish.exceptions import InvalidPublishMetadataError
from services.publish.settings import PublishSettings


class PublishMetadataBuilder:
    """Builds platform-agnostic and platform-specific publish metadata."""

    def __init__(self, settings: PublishSettings | None = None) -> None:
        self._settings = settings or PublishSettings.from_django_settings()

    def build(self, context: EpisodePublishContext) -> PublishMetadata:
        """Build complete metadata for an episode publish context."""
        title = self.build_title(context.title)
        description = self.build_description(context)
        summary = self.build_summary(context)
        slug = self.build_slug(title, context.episode_id)
        tags = self.build_tags(context)
        rss_item = self.build_rss_item(context, title, description, slug)
        youtube = self.build_youtube_metadata(context, title, description, tags)

        return PublishMetadata(
            title=title,
            description=description,
            summary=summary,
            slug=slug,
            tags=tags,
            language=context.language,
            duration_seconds=context.duration_seconds,
            rss_item=rss_item,
            youtube=youtube,
        )

    def build_title(self, title: str) -> str:
        """Normalize episode title for publishing."""
        normalized = title.strip()
        if not normalized:
            raise InvalidPublishMetadataError("Episode title cannot be empty.")
        return normalized[:500]

    def build_description(self, context: EpisodePublishContext) -> str:
        """Build episode description for feeds and platforms."""
        if context.description.strip():
            return context.description.strip()
        if context.summary.strip():
            return context.summary.strip()
        return context.title.strip()

    def build_summary(self, context: EpisodePublishContext) -> str:
        """Build short summary text."""
        if context.summary.strip():
            return context.summary.strip()
        description = self.build_description(context)
        return description[:280]

    def build_slug(self, title: str, episode_id: UUID) -> str:
        """Build a URL-safe slug for the episode."""
        normalized = unicodedata.normalize("NFKD", title)
        ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
        slug_base = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_title.lower()).strip("-")
        if not slug_base:
            slug_base = "episode"
        return f"{slug_base}-{str(episode_id)[:8]}"

    def build_tags(self, context: EpisodePublishContext) -> tuple[str, ...]:
        """Build tag list from episode metadata."""
        tags: list[str] = ["podcast", "ai", context.language]
        if context.summary:
            words = re.findall(r"[A-Za-z]{4,}", context.summary)
            tags.extend(word.lower() for word in words[:5])
        return tuple(dict.fromkeys(tag for tag in tags if tag))

    def build_enclosure(self, context: EpisodePublishContext) -> EnclosureMetadata:
        """Build RSS enclosure metadata."""
        length = context.audio_file_size or 0
        return EnclosureMetadata(
            url=context.audio_url,
            length=length,
            mime_type=context.audio_mime_type,
            duration_seconds=context.duration_seconds,
        )

    def build_rss_item(
        self,
        context: EpisodePublishContext,
        title: str,
        description: str,
        slug: str,
    ) -> RSSItemFields:
        """Build RSS item fields for an episode."""
        pub_date = context.publish_date or timezone.now()
        if isinstance(pub_date, datetime):
            resolved_pub_date = pub_date
        else:
            resolved_pub_date = datetime.combine(
                pub_date,
                datetime.min.time(),
                tzinfo=timezone.get_current_timezone(),
            )

        site_base = self._settings.rss_feed_site_url.rstrip("/")
        link = f"{site_base}/episodes/{slug}"
        guid = f"{site_base}/episodes/{context.episode_id}"

        return RSSItemFields(
            title=title,
            description=description,
            link=link,
            guid=guid,
            pub_date=resolved_pub_date,
            enclosure=self.build_enclosure(context),
            slug=slug,
        )

    def build_youtube_metadata(
        self,
        context: EpisodePublishContext,
        title: str,
        description: str,
        tags: tuple[str, ...],
    ) -> YouTubeMetadataFields:
        """Build YouTube-specific metadata sections."""
        sections = [
            description,
            "",
            "Episode details:",
            f"- Duration: {context.duration_seconds} seconds",
            f"- Language: {context.language}",
        ]
        if context.summary:
            sections.extend(["", "Summary:", context.summary])

        youtube_description = "\n".join(sections).strip()
        return YouTubeMetadataFields(
            title=title[:100],
            description=youtube_description[:5000],
            tags=tags[:15],
        )

    def build_metadata_summary(self, metadata: PublishMetadata) -> dict[str, Any]:
        """Return a compact metadata summary for logging."""
        return {
            "title": metadata.title,
            "slug": metadata.slug,
            "duration_seconds": metadata.duration_seconds,
            "tags": list(metadata.tags),
            "language": metadata.language,
        }
