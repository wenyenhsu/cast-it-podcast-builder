"""RSS feed XML generation."""

import logging
from datetime import datetime
from email.utils import format_datetime
from pathlib import Path
from typing import Any
from xml.dom import minidom
from xml.etree import ElementTree as ET

from django.utils import timezone

from apps.publish.models import PublishedEpisode
from domain.publish.dtos import RSSItemFields
from domain.publish.exceptions import FeedGenerationError
from services.publish.settings import PublishSettings

logger = logging.getLogger(__name__)

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM_NS = "http://www.w3.org/2005/Atom"


class RSSFeedGenerator:
    """Generates podcast RSS feed XML from published episodes."""

    def __init__(self, settings: PublishSettings | None = None) -> None:
        self._settings = settings or PublishSettings.from_django_settings()

    def generate(self, *, episodes: list[PublishedEpisode] | None = None) -> str:
        """Generate RSS feed XML for published episodes."""
        if episodes is not None:
            published = episodes
        else:
            published = self._load_published_episodes()
        try:
            root = ET.Element("rss", {"version": "2.0"})
            root.set("xmlns:itunes", ITUNES_NS)
            root.set("xmlns:atom", ATOM_NS)

            channel = ET.SubElement(root, "channel")
            self._append_channel_metadata(channel)
            for record in published:
                item_fields = self._item_fields_from_record(record)
                self._append_item(channel, item_fields)

            xml_bytes = ET.tostring(root, encoding="unicode")
            return self._prettify(xml_bytes)
        except FeedGenerationError:
            raise
        except Exception as exc:
            raise FeedGenerationError(f"Failed to generate RSS feed: {exc}") from exc

    def write_feed(self, *, episodes: list[PublishedEpisode] | None = None) -> Path:
        """Generate and persist the RSS feed file."""
        xml = self.generate(episodes=episodes)
        output_path = self._settings.resolve_feed_output_path()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(xml, encoding="utf-8")
        episode_list = self._load_published_episodes() if episodes is None else episodes
        logger.info(
            "RSS feed written",
            extra={
                "event": "rss_feed_written",
                "output_path": str(output_path),
                "item_count": len(episode_list),
            },
        )
        return output_path

    def _load_published_episodes(self) -> list[PublishedEpisode]:
        return list(
            PublishedEpisode.objects.filter(platform="rss")
            .select_related("episode")
            .order_by("-published_at")[:100]
        )

    def _append_channel_metadata(self, channel: ET.Element) -> None:
        ET.SubElement(channel, "title").text = self._settings.rss_feed_title
        ET.SubElement(channel, "link").text = self._settings.rss_feed_site_url
        ET.SubElement(channel, "description").text = self._settings.rss_feed_subtitle
        ET.SubElement(channel, "language").text = self._settings.rss_feed_language
        ET.SubElement(
            channel,
            f"{{{ITUNES_NS}}}author",
        ).text = self._settings.rss_feed_author
        ET.SubElement(
            channel,
            f"{{{ITUNES_NS}}}summary",
        ).text = self._settings.rss_feed_subtitle
        atom_link = ET.SubElement(
            channel,
            f"{{{ATOM_NS}}}link",
        )
        atom_link.set("href", self._settings.rss_feed_site_url)
        atom_link.set("rel", "self")
        atom_link.set("type", "application/rss+xml")

    def _append_item(self, channel: ET.Element, item_fields: RSSItemFields) -> None:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = item_fields.title
        ET.SubElement(item, "description").text = item_fields.description
        ET.SubElement(item, "link").text = item_fields.link
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = item_fields.guid
        ET.SubElement(item, "pubDate").text = format_datetime(
            self._ensure_aware(item_fields.pub_date)
        )
        enclosure = ET.SubElement(item, "enclosure")
        enclosure.set("url", item_fields.enclosure.url)
        enclosure.set("length", str(item_fields.enclosure.length))
        enclosure.set("type", item_fields.enclosure.mime_type)
        ET.SubElement(
            item,
            f"{{{ITUNES_NS}}}duration",
        ).text = str(item_fields.enclosure.duration_seconds)

    def _item_fields_from_record(self, record: PublishedEpisode) -> RSSItemFields:
        metadata: dict[str, Any] = record.metadata or {}
        rss_meta = metadata.get("rss_item", {})
        enclosure_meta = rss_meta.get("enclosure", {})
        pub_date_raw = rss_meta.get("pub_date")
        pub_date = self._parse_pub_date(pub_date_raw, record.published_at)

        from domain.publish.dtos import EnclosureMetadata

        enclosure = EnclosureMetadata(
            url=rss_meta.get("enclosure_url", record.published_url),
            length=int(enclosure_meta.get("length", 0)),
            mime_type=enclosure_meta.get("mime_type", "audio/mpeg"),
            duration_seconds=int(
                enclosure_meta.get(
                    "duration_seconds",
                    record.episode.duration_seconds or 0,
                )
            ),
        )
        return RSSItemFields(
            title=rss_meta.get("title", record.episode.title),
            description=rss_meta.get(
                "description",
                record.episode.description or record.episode.summary,
            ),
            link=rss_meta.get("link", record.published_url),
            guid=rss_meta.get("guid", record.published_url),
            pub_date=pub_date,
            enclosure=enclosure,
            slug=rss_meta.get("slug", str(record.episode_id)),
        )

    def _parse_pub_date(self, raw: Any, fallback: datetime) -> datetime:
        if isinstance(raw, datetime):
            return self._ensure_aware(raw)
        if isinstance(raw, str):
            try:
                parsed = datetime.fromisoformat(raw)
                return self._ensure_aware(parsed)
            except ValueError:
                pass
        return self._ensure_aware(fallback)

    def _ensure_aware(self, value: datetime) -> datetime:
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_current_timezone())
        return value

    def _prettify(self, xml: str) -> str:
        parsed = minidom.parseString(xml.encode("utf-8"))
        return parsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
