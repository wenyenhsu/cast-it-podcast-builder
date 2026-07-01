"""Document normalization for knowledge indexing."""

from typing import Any

from apps.articles.models import Article
from apps.episodes.models import Episode
from apps.knowledge.models import SourceType
from apps.scripts.models import Script
from domain.knowledge.dtos import DocumentIndexRequest


class DocumentNormalizer:
    """Converts domain entities into knowledge document index requests."""

    def from_article(self, article: Article) -> DocumentIndexRequest:
        content = _join_sections(
            article.title,
            article.summary,
            article.content,
        )
        metadata: dict[str, Any] = {
            "category": article.category,
            "tags": list(article.tags.values_list("slug", flat=True)),
            "importance_score": article.importance_score,
        }
        if article.published_at:
            metadata["publish_date"] = article.published_at.date().isoformat()
        if article.source_id:
            metadata["source_name"] = article.source.name

        return DocumentIndexRequest(
            source_type=SourceType.ARTICLE,
            source_id=str(article.id),
            title=article.title,
            language=article.language,
            content=content,
            metadata=metadata,
        )

    def from_episode(self, episode: Episode) -> DocumentIndexRequest:
        content = _join_sections(
            episode.title,
            episode.summary,
            episode.description,
        )
        metadata: dict[str, Any] = {
            "episode_id": str(episode.id),
            "status": episode.status,
        }
        if episode.publish_date:
            metadata["publish_date"] = episode.publish_date.isoformat()

        return DocumentIndexRequest(
            source_type=SourceType.EPISODE,
            source_id=str(episode.id),
            title=episode.title,
            language=episode.language,
            content=content,
            metadata=metadata,
        )

    def from_script(self, script: Script) -> DocumentIndexRequest:
        segments = script.segments.order_by("sequence")
        segment_text = "\n\n".join(
            f"{segment.speaker}: {segment.text}" for segment in segments
        )
        content = _join_sections(script.episode.title, segment_text)
        metadata: dict[str, Any] = {
            "episode_id": str(script.episode_id),
            "script_version": script.version,
            "llm_provider": script.llm_provider,
            "model_name": script.model_name,
        }

        return DocumentIndexRequest(
            source_type=SourceType.SCRIPT,
            source_id=str(script.id),
            title=script.episode.title,
            language=script.episode.language,
            content=content,
            metadata=metadata,
        )

    def from_newsletter(
        self,
        *,
        source_id: str,
        title: str,
        language: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentIndexRequest:
        return DocumentIndexRequest(
            source_type=SourceType.NEWSLETTER,
            source_id=source_id,
            title=title,
            language=language,
            content=content,
            metadata=metadata or {},
        )

    def from_documentation(
        self,
        *,
        source_id: str,
        title: str,
        language: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> DocumentIndexRequest:
        return DocumentIndexRequest(
            source_type=SourceType.DOCUMENTATION,
            source_id=source_id,
            title=title,
            language=language,
            content=content,
            metadata=metadata or {},
        )


def _join_sections(*sections: str) -> str:
    return "\n\n".join(section.strip() for section in sections if section.strip())
