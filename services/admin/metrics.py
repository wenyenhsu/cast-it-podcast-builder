"""Operational metrics for the admin metrics dashboard."""

from datetime import timedelta
from typing import Any

from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.utils import timezone

from apps.articles.models import Article
from apps.publish.models import PublishedEpisode, PublishJob, PublishJobStatus
from apps.scheduler.models import Job, JobStatus, JobType


class MetricsService:
    """Calculates pipeline metrics for operations reporting."""

    def summary(self, *, days: int = 7) -> dict[str, Any]:
        since = timezone.now() - timedelta(days=days)
        return {
            "period_days": days,
            "average_script_generation_seconds": self._avg_job_duration(
                JobType.GENERATE_SCRIPT,
                since,
            ),
            "average_audio_generation_seconds": self._avg_job_duration(
                JobType.GENERATE_AUDIO,
                since,
            ),
            "average_publish_seconds": self._avg_publish_duration(since),
            "failure_rate_percent": self._failure_rate(since),
            "retry_rate_percent": self._retry_rate(since),
            "articles_imported_per_day": self._daily_counts(
                Article.objects.filter(created_at__gte=since),
                "created_at__date",
            ),
            "episodes_published_per_day": self._daily_counts(
                PublishedEpisode.objects.filter(published_at__gte=since),
                "published_at__date",
            ),
        }

    def _avg_job_duration(self, job_type: str, since) -> float | None:
        jobs = Job.objects.filter(
            job_type=job_type,
            status=JobStatus.SUCCEEDED,
            started_at__isnull=False,
            completed_at__isnull=False,
            completed_at__gte=since,
        ).annotate(
            duration=ExpressionWrapper(
                F("completed_at") - F("started_at"),
                output_field=DurationField(),
            )
        )
        avg = jobs.aggregate(avg=Avg("duration"))["avg"]
        if avg is None:
            return None
        return round(avg.total_seconds(), 2)

    def _avg_publish_duration(self, since) -> float | None:
        jobs = PublishJob.objects.filter(
            status=PublishJobStatus.COMPLETED,
            started_at__isnull=False,
            completed_at__isnull=False,
            completed_at__gte=since,
        ).annotate(
            duration=ExpressionWrapper(
                F("completed_at") - F("started_at"),
                output_field=DurationField(),
            )
        )
        avg = jobs.aggregate(avg=Avg("duration"))["avg"]
        if avg is None:
            return None
        return round(avg.total_seconds(), 2)

    def _failure_rate(self, since) -> float:
        total = Job.objects.filter(created_at__gte=since).count()
        if total == 0:
            return 0.0
        failed = Job.objects.filter(
            created_at__gte=since,
            status=JobStatus.FAILED,
        ).count()
        return round((failed / total) * 100, 2)

    def _retry_rate(self, since) -> float:
        total = Job.objects.filter(created_at__gte=since).count()
        if total == 0:
            return 0.0
        retried = Job.objects.filter(
            created_at__gte=since,
            retry_count__gt=0,
        ).count()
        return round((retried / total) * 100, 2)

    def _daily_counts(self, queryset, date_field: str) -> list[dict[str, Any]]:
        rows = (
            queryset.values(date_field).annotate(count=Count("id")).order_by(date_field)
        )
        return [{"date": str(row[date_field]), "count": row["count"]} for row in rows]
