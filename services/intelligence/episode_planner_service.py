"""Episode planning service."""

import logging
import time
from typing import TYPE_CHECKING
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from domain.intelligence.constants import (
    ESTIMATED_SECONDS_PER_ARTICLE,
    MAX_EPISODE_ARTICLES,
    MAX_EPISODE_SECONDS,
)
from domain.intelligence.dtos import EpisodePlanDTO, RankedArticle, TopicCluster
from domain.llm.dtos import LLMRequest
from services.intelligence.parsers import parse_single_line
from services.llm.prompt_builder import PromptBuilder

if TYPE_CHECKING:
    from services.llm.service import LLMService

logger = logging.getLogger(__name__)


class EpisodePlannerService:
    """Selects articles and creates a planned episode."""

    def __init__(
        self,
        llm_service: "LLMService",
        prompt_builder: PromptBuilder | None = None,
    ) -> None:
        self._llm = llm_service
        self._prompt_builder = prompt_builder or PromptBuilder()

    def plan_episode(
        self,
        ranked_articles: list[RankedArticle],
        articles: list[Article],
        clusters: list[TopicCluster],
        *,
        language: str = "en",
    ) -> EpisodePlanDTO:
        """Create an episode from ranked articles."""
        started = time.perf_counter()
        article_map = {article.id: article for article in articles}
        selected_ids = self._select_articles(ranked_articles, article_map, clusters)
        selected_articles = [article_map[article_id] for article_id in selected_ids]

        title = self._generate_title(selected_articles, language)
        summary = self._generate_summary(title, selected_articles, language)
        estimated_duration = min(
            MAX_EPISODE_SECONDS,
            len(selected_articles) * ESTIMATED_SECONDS_PER_ARTICLE,
        )

        with transaction.atomic():
            episode = Episode.objects.create(
                title=title,
                description=summary,
                summary=summary,
                language=language,
                publish_date=timezone.now().date(),
                status=EpisodeStatus.DRAFT,
                duration_seconds=estimated_duration,
            )
            for article in selected_articles:
                EpisodeArticle.objects.create(episode=episode, article=article)
                article.status = ArticleStatus.SELECTED
                article.save(update_fields=["status", "updated_at"])

        elapsed = time.perf_counter() - started
        logger.info(
            "Episode created",
            extra={
                "event": "episode_created",
                "episode_id": str(episode.id),
                "article_count": len(selected_ids),
                "elapsed_time": elapsed,
            },
        )

        return EpisodePlanDTO(
            episode_id=episode.id,
            title=title,
            summary=summary,
            article_ids=selected_ids,
            estimated_duration_seconds=estimated_duration,
            language=language,
        )

    def _select_articles(
        self,
        ranked_articles: list[RankedArticle],
        article_map: dict[UUID, Article],
        clusters: list[TopicCluster],
    ) -> list[UUID]:
        selected: list[UUID] = []
        used_clusters: set[str] = set()
        seen_titles: set[str] = set()

        cluster_members = self._cluster_membership(clusters)

        for ranked in ranked_articles:
            if len(selected) >= MAX_EPISODE_ARTICLES:
                break

            article = article_map.get(ranked.article_id)
            if article is None:
                continue

            normalized_title = self._normalize_title(article.title)
            if normalized_title in seen_titles:
                continue

            cluster_id = ranked.cluster_id or cluster_members.get(article.id, "")
            if cluster_id and cluster_id in used_clusters:
                continue

            selected.append(article.id)
            seen_titles.add(normalized_title)
            if cluster_id:
                used_clusters.add(cluster_id)

        return selected

    def _generate_title(self, articles: list[Article], language: str) -> str:
        if not articles:
            return "Daily Tech Briefing"

        user_prompt = self._prompt_builder.build_user_prompt(
            "episode_title",
            {
                "language": language,
                "articles": self._format_articles(articles),
            },
        )
        system_prompt = self._prompt_builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": language},
        )
        response = self._llm.chat(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        return parse_single_line(response.content)

    def _generate_summary(
        self,
        title: str,
        articles: list[Article],
        language: str,
    ) -> str:
        user_prompt = self._prompt_builder.build_user_prompt(
            "episode_summary",
            {
                "title": title,
                "language": language,
                "articles": self._format_articles(articles),
            },
        )
        system_prompt = self._prompt_builder.build_system_prompt(
            "system",
            {"show_name": "Cast It", "language": language},
        )
        response = self._llm.chat(
            LLMRequest(system_prompt=system_prompt, user_prompt=user_prompt)
        )
        return parse_single_line(response.content)

    @staticmethod
    def _format_articles(articles: list[Article]) -> str:
        lines: list[str] = []
        for article in articles:
            lines.append(
                f"- {article.title} ({article.category or 'Other'}): "
                f"{article.summary or article.content[:200]}"
            )
        return "\n".join(lines)

    @staticmethod
    def _normalize_title(title: str) -> str:
        return " ".join(title.lower().split())

    @staticmethod
    def _cluster_membership(clusters: list[TopicCluster]) -> dict[UUID, str]:
        membership: dict[UUID, str] = {}
        for cluster in clusters:
            for article_id in cluster.article_ids:
                membership[article_id] = cluster.cluster_id
        return membership
