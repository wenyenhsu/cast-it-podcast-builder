"""Article library management for the operations content dashboard."""

from typing import TYPE_CHECKING, Any

from django.utils import timezone

from apps.articles.models import Article
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import ProviderType
from apps.scheduler.models import Job, JobStatus
from apps.scripts.models import Script, ScriptStatus
from domain.jobs.exceptions import JobCancellationError
from services.admin.dispatch import AdminJobDispatchService
from services.admin.job_progress import JobProgressService
from services.jobs.job_service import CANCELLABLE_STATUSES

if TYPE_CHECKING:
    from apps.scheduler.models import Job


class ContentLibraryError(Exception):
    """Raised when content library actions fail validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ContentLibraryService:
    """Lists articles and manages script source selection."""

    def article_totals(self) -> dict[str, int]:
        return {
            "total_articles": Article.objects.count(),
            "rss_articles": Article.objects.filter(
                source__provider_type=ProviderType.RSS
            ).count(),
            "manual_articles": Article.objects.filter(
                source__provider_type=ProviderType.MANUAL
            ).count(),
            "selected_for_script": Article.objects.filter(
                selected_for_script=True
            ).count(),
        }

    def list_articles(
        self,
        *,
        provider_type: str | None = None,
    ) -> list[dict[str, Any]]:
        articles = Article.objects.select_related("source").order_by("-created_at")
        if provider_type:
            articles = articles.filter(source__provider_type=provider_type)
        return [
            {
                "id": str(article.id),
                "title": article.title,
                "source_name": article.source.name if article.source else "—",
                "provider_type": (
                    article.source.provider_type if article.source else ""
                ),
                "created_at": article.created_at,
                "status": article.status,
                "selected_for_script": article.selected_for_script,
            }
            for article in articles
        ]

    def update_script_selection(
        self,
        *,
        selected_ids: set[str],
        scope_ids: set[str],
    ) -> int:
        articles = Article.objects.filter(id__in=scope_ids)
        updated = 0
        for article in articles:
            should_select = str(article.id) in selected_ids
            if article.selected_for_script != should_select:
                article.selected_for_script = should_select
                article.save(update_fields=["selected_for_script", "updated_at"])
                updated += 1
        return updated

    def _draft_episode(self) -> Episode | None:
        return (
            Episode.objects.filter(
                status__in=[EpisodeStatus.DRAFT, EpisodeStatus.COLLECTING]
            )
            .order_by("-created_at")
            .first()
        )

    def ensure_draft_episode(self) -> Episode:
        episode = self._draft_episode()
        if episode is not None:
            return episode
        return Episode.objects.create(
            title=f"Draft {timezone.localdate()}",
            status=EpisodeStatus.DRAFT,
        )

    def script_workspace(self) -> dict[str, Any]:
        episode = self._draft_episode()
        latest_script: Script | None = None
        if episode is not None:
            latest_script = episode.scripts.order_by("-version").first()
        selected_count = Article.objects.filter(selected_for_script=True).count()
        latest_ready_script_id = ""
        if episode is not None:
            ready_script = (
                episode.scripts.filter(
                    status__in=[ScriptStatus.READY, ScriptStatus.APPROVED]
                )
                .order_by("-version")
                .first()
            )
            if ready_script is not None:
                latest_ready_script_id = str(ready_script.id)
        progress_service = JobProgressService()
        active_script_job = progress_service.find_any_active_script_job()
        return {
            "episode_id": str(episode.id) if episode else "",
            "episode_title": episode.title if episode else "",
            "episode_status": episode.status if episode else "",
            "linked_articles": episode.articles.count() if episode else 0,
            "selected_for_script": selected_count,
            "can_generate": selected_count > 0
            and active_script_job is None,
            "latest_script_version": latest_script.version if latest_script else None,
            "latest_script_status": latest_script.status if latest_script else "",
            "latest_ready_script_id": latest_ready_script_id,
            "can_open_tts": bool(latest_ready_script_id),
            "active_script_job_id": str(active_script_job.id)
            if active_script_job
            else "",
            "can_abort_script": active_script_job is not None
            and active_script_job.status in CANCELLABLE_STATUSES,
            "script_job_status": active_script_job.status if active_script_job else "",
        }

    def sync_selected_articles_to_draft_episode(
        self,
        episode: Episode | None = None,
    ) -> str | None:
        target = episode or self._draft_episode()
        if target is None:
            return None

        selected_articles = list(
            Article.objects.filter(selected_for_script=True).order_by("-created_at")
        )
        selected_ids = {article.id for article in selected_articles}
        EpisodeArticle.objects.filter(episode=target).exclude(
            article_id__in=selected_ids
        ).delete()
        for article in selected_articles:
            EpisodeArticle.objects.get_or_create(episode=target, article=article)
        return str(target.id)

    def queue_script_generation(self, *, episode_title: str) -> tuple[str, str]:
        selected_count = Article.objects.filter(selected_for_script=True).count()
        if selected_count == 0:
            raise ContentLibraryError(
                "Select at least one article as script source before generating."
            )

        title = episode_title.strip()
        if not title:
            raise ContentLibraryError("Episode name is required.")

        active_job = JobProgressService().find_any_active_script_job()
        if active_job is not None:
            raise ContentLibraryError(
                "Script generation is already running. Wait for it to finish or dismiss the job panel."
            )

        episode = Episode.objects.create(title=title, status=EpisodeStatus.DRAFT)

        self.sync_selected_articles_to_draft_episode(episode)
        if episode.articles.count() == 0:
            episode.delete()
            raise ContentLibraryError(
                "Select at least one article as script source before generating."
            )

        job = AdminJobDispatchService().generate_script(str(episode.id))
        return str(episode.id), str(job.id)

    def abort_script_generation(self) -> str:
        episode = self._draft_episode()
        if episode is None:
            raise ContentLibraryError("No draft episode found.")

        active_job = JobProgressService().find_active_script_job(str(episode.id))
        if active_job is None:
            raise ContentLibraryError("No active script generation job to abort.")

        try:
            AdminJobDispatchService().cancel_job(active_job)
        except JobCancellationError as exc:
            raise ContentLibraryError(str(exc)) from exc

        return str(active_job.id)

    def delete_episode(self, episode_id: str) -> str:
        episode = Episode.objects.filter(pk=episode_id).first()
        if episode is None:
            raise ContentLibraryError("Episode not found.")
        title = episode.title
        episode.delete()
        return title

    def delete_failed_job(self, job_id: str) -> str:
        job = Job.objects.filter(pk=job_id, status=JobStatus.FAILED).first()
        if job is None:
            raise ContentLibraryError("Failed job not found or already cleared.")
        label = JobProgressService().label_for(job.job_type)
        job.delete()
        return label
