"""Dashboard statistics for the operations admin index."""

from typing import Any

from django.db.models import Count, Q
from django.utils import timezone

from apps.articles.models import Article
from apps.episodes.models import Episode, EpisodeStatus
from apps.providers.models import ProviderHealthCheck
from apps.publish.models import PublishedEpisode, PublishJobStatus
from apps.scheduler.models import Job, JobStatus
from apps.scripts.models import Script, ScriptStatus
from services.admin.job_progress import JobProgressService
from services.episodes.status_sync import episode_display_status


class DashboardStatsService:
    """Computes overview statistics for the admin dashboard."""

    def overview(self) -> dict[str, Any]:
        today = timezone.now().date()
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        job_counts = dict(
            Job.objects.values("status")
            .annotate(total=Count("id"))
            .values_list("status", "total")
        )
        provider_health = self._provider_health_summary()

        return {
            "total_articles": Article.objects.count(),
            "articles_imported_today": Article.objects.filter(
                created_at__gte=start_of_day
            ).count(),
            "pending_jobs": job_counts.get(JobStatus.PENDING, 0),
            "queued_jobs": job_counts.get(JobStatus.QUEUED, 0),
            "running_jobs": job_counts.get(JobStatus.RUNNING, 0),
            "failed_jobs": job_counts.get(JobStatus.FAILED, 0),
            "episodes_generated_today": Episode.objects.filter(
                created_at__date=today
            ).count(),
            "episodes_waiting_for_publishing": Episode.objects.filter(
                status=EpisodeStatus.PUBLISHING
            ).count()
            + Episode.objects.filter(status=EpisodeStatus.COMPLETED)
            .exclude(publish_jobs__status=PublishJobStatus.COMPLETED)
            .distinct()
            .count(),
            "published_episodes": PublishedEpisode.objects.count(),
            "scripts_total": Script.objects.count(),
            "provider_health": provider_health,
        }

    def list_failed_jobs(self, *, limit: int = 50) -> list[dict[str, Any]]:
        progress = JobProgressService()
        jobs = Job.objects.filter(status=JobStatus.FAILED).order_by("-updated_at")[
            :limit
        ]
        return [self._serialize_job(job, progress) for job in jobs]

    def list_episodes_today(self, *, limit: int = 50) -> list[dict[str, Any]]:
        start_of_day = timezone.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        episodes = (
            Episode.objects.filter(
                Q(created_at__gte=start_of_day) | Q(updated_at__gte=start_of_day)
            )
            .order_by("-updated_at")[:limit]
        )
        return [self._serialize_episode(episode) for episode in episodes]

    @staticmethod
    def _serialize_job(job: Job, progress: JobProgressService) -> dict[str, Any]:
        payload = job.payload or {}
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "label": progress.label_for(job.job_type),
            "status": job.status,
            "error_message": job.error_message or "—",
            "retry_count": job.retry_count,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "episode_id": str(payload.get("episode_id", "") or ""),
            "script_id": str(payload.get("script_id", "") or ""),
        }

    @staticmethod
    def _serialize_episode(episode: Episode) -> dict[str, Any]:
        tts_script = (
            episode.scripts.filter(
                status__in=[ScriptStatus.READY, ScriptStatus.APPROVED]
            )
            .order_by("-version")
            .first()
        )
        tts_script_id = str(tts_script.id) if tts_script else ""
        return {
            "id": str(episode.id),
            "title": episode.title,
            "status": episode.status,
            "display_status": episode_display_status(episode),
            "created_at": episode.created_at,
            "updated_at": episode.updated_at,
            "tts_script_id": tts_script_id,
            "can_generate_tts": bool(tts_script_id),
        }

    def _provider_health_summary(self) -> list[dict[str, Any]]:
        checks = (
            ProviderHealthCheck.objects.order_by(
                "provider_name", "-checked_at"
            ).distinct("provider_name")
            if _supports_distinct_on()
            else ProviderHealthCheck.objects.order_by("-checked_at")[:20]
        )
        summary: list[dict[str, Any]] = []
        seen: set[str] = set()
        for check in checks:
            if check.provider_name in seen:
                continue
            seen.add(check.provider_name)
            summary.append(
                {
                    "name": check.provider_name,
                    "status": check.status,
                    "checked_at": check.checked_at,
                }
            )
        if not summary:
            summary = [
                {"name": "No checks recorded", "status": "unknown", "checked_at": None}
            ]
        return summary


def _supports_distinct_on() -> bool:
    try:
        from django.db import connection

        return connection.vendor == "postgresql"
    except Exception:
        return False
