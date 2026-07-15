"""Remove leftover Celery Beat entries for automatic script generation."""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

from apps.scheduler.models import Job, JobStatus, JobType


class Command(BaseCommand):
    help = (
        "Disable automatic script generation schedules and clear stuck script jobs. "
        "Manual Generate Script from Content remains available."
    )

    def handle(self, *args, **options) -> None:
        removed = PeriodicTask.objects.filter(name="daily-script-generation").delete()
        disabled = PeriodicTask.objects.filter(
            task__icontains="generate_script_scheduled"
        ).update(enabled=False)

        stuck = Job.objects.filter(
            job_type=JobType.GENERATE_SCRIPT,
            status__in=[
                JobStatus.PENDING,
                JobStatus.QUEUED,
                JobStatus.RUNNING,
                JobStatus.RETRYING,
            ],
        )
        stuck_count = stuck.count()
        stuck.update(
            status=JobStatus.CANCELLED,
            error_message="Cleared: automatic script scheduling disabled.",
            completed_at=timezone.now(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Pruned script schedule: "
                f"deleted={removed[0]}, disabled={disabled}, cancelled_jobs={stuck_count}."
            )
        )
