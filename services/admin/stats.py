"""Dashboard statistics for the operations admin index."""

from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.articles.models import Article
from apps.episodes.models import Episode, EpisodeStatus
from apps.providers.models import ProviderHealthCheck
from apps.publish.models import PublishedEpisode, PublishJobStatus
from apps.scheduler.models import Job, JobStatus


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
            "episodes_waiting_for_audio": Episode.objects.filter(
                status=EpisodeStatus.GENERATING_AUDIO
            ).count()
            + Episode.objects.filter(status=EpisodeStatus.GENERATING_SCRIPT).count(),
            "episodes_waiting_for_publishing": Episode.objects.filter(
                status=EpisodeStatus.PUBLISHING
            ).count()
            + Episode.objects.filter(status=EpisodeStatus.COMPLETED)
            .exclude(publish_jobs__status=PublishJobStatus.COMPLETED)
            .distinct()
            .count(),
            "published_episodes": PublishedEpisode.objects.count(),
            "provider_health": provider_health,
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
