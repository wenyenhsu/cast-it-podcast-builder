"""Publishing data transfer objects."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class EpisodePublishContext:
    """Episode and audio context required for publishing."""

    episode_id: UUID
    title: str
    description: str
    summary: str
    language: str
    duration_seconds: int
    publish_date: datetime | None
    cover_image: str
    audio_file_path: Path
    audio_url: str
    audio_format: str
    audio_file_size: int | None
    audio_mime_type: str


@dataclass(frozen=True)
class EnclosureMetadata:
    """RSS enclosure metadata for an episode."""

    url: str
    length: int
    mime_type: str
    duration_seconds: int


@dataclass(frozen=True)
class RSSItemFields:
    """RSS item fields for a single episode."""

    title: str
    description: str
    link: str
    guid: str
    pub_date: datetime
    enclosure: EnclosureMetadata
    slug: str


@dataclass(frozen=True)
class YouTubeMetadataFields:
    """YouTube-specific metadata fields."""

    title: str
    description: str
    tags: tuple[str, ...]
    category_id: str = "22"
    privacy_status: str = "public"


@dataclass(frozen=True)
class PublishMetadata:
    """Unified metadata reusable across publishing platforms."""

    title: str
    description: str
    summary: str
    slug: str
    tags: tuple[str, ...]
    language: str
    duration_seconds: int
    rss_item: RSSItemFields
    youtube: YouTubeMetadataFields
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublishRequest:
    """Request to publish an episode to one or more platforms."""

    episode_id: UUID
    platforms: tuple[str, ...] = ()


@dataclass(frozen=True)
class PublishResult:
    """Result of a successful publish operation."""

    platform: str
    published_url: str
    external_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PublishEpisodeResult:
    """Aggregate result for publishing an episode."""

    episode_id: UUID
    platform_results: tuple[PublishResult, ...]
    publish_job_ids: tuple[UUID, ...]
