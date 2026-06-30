"""Admin configuration for providers app."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin
from apps.providers.models import NewsSource, ProviderHealthCheck
from apps.scheduler.models import Job, JobStatus, JobType


@admin.register(NewsSource)
class NewsSourceAdmin(AdminActionMixin, admin.ModelAdmin):
    list_display = (
        "name",
        "provider_type",
        "language",
        "max_articles_per_import",
        "enabled",
        "last_successful_import",
        "last_failed_import",
        "created_at",
    )
    list_filter = ("provider_type", "language", "enabled")
    search_fields = ("name", "homepage", "rss_url")
    list_editable = ("enabled",)
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_successful_import",
        "last_failed_import",
    )
    ordering = ("name",)
    list_per_page = 25
    actions = (
        "enable_sources",
        "disable_sources",
        "import_selected",
        "health_check_selected",
    )

    def last_successful_import(self, obj: NewsSource) -> str:
        job = self._last_import_job(obj, succeeded=True)
        return str(job.completed_at) if job and job.completed_at else "—"

    @admin.display(description="Last Failed Import")
    def last_failed_import(self, obj: NewsSource) -> str:
        job = self._last_import_job(obj, succeeded=False)
        return str(job.completed_at) if job and job.completed_at else "—"

    def _last_import_job(self, source: NewsSource, *, succeeded: bool) -> Job | None:
        status = JobStatus.SUCCEEDED if succeeded else JobStatus.FAILED
        return (
            Job.objects.filter(
                job_type=JobType.IMPORT_NEWS,
                status=status,
                payload__source_id=str(source.id),
            )
            .order_by("-completed_at")
            .first()
        )

    @admin.action(description="Enable selected sources")
    def enable_sources(
        self,
        request: HttpRequest,
        queryset: QuerySet[NewsSource],
    ) -> None:
        queryset.update(enabled=True)
        self.action_logger.log(
            action="enable_sources",
            user_id=self._user_id(request),
            resource_type="news_source",
            resource_ids=self._selected_ids(queryset),
        )

    @admin.action(description="Disable selected sources")
    def disable_sources(
        self,
        request: HttpRequest,
        queryset: QuerySet[NewsSource],
    ) -> None:
        queryset.update(enabled=False)
        self.action_logger.log(
            action="disable_sources",
            user_id=self._user_id(request),
            resource_type="news_source",
            resource_ids=self._selected_ids(queryset),
        )

    @admin.action(description="Import selected sources")
    def import_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[NewsSource],
    ) -> None:
        job_ids = self.action_service.import_sources(
            queryset,
            user_id=self._user_id(request),
        )
        self._message_jobs(request, job_ids, detail="Manual import queued.")

    @admin.action(description="Health check selected sources")
    def health_check_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[NewsSource],
    ) -> None:
        job_ids = self.action_service.health_check_sources(
            queryset,
            user_id=self._user_id(request),
        )
        self._message_jobs(request, job_ids, detail="Health checks queued.")


@admin.register(ProviderHealthCheck)
class ProviderHealthCheckAdmin(admin.ModelAdmin):
    list_display = (
        "provider_name",
        "provider_type",
        "status_display",
        "response_time_ms",
        "checked_at",
        "news_source",
    )
    list_filter = ("provider_type", "status")
    search_fields = ("provider_name", "details")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-checked_at",)

    @admin.display(description="Status")
    def status_display(self, obj: ProviderHealthCheck) -> str:
        return status_badge(obj.status)
