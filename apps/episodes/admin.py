"""Admin configuration for episodes app."""

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html

from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin
from apps.episodes.models import Episode, EpisodeArticle
from apps.scheduler.models import Job, JobStatus


class EpisodeArticleInline(admin.TabularInline):
    model = EpisodeArticle
    extra = 1
    autocomplete_fields = ("article",)


@admin.register(Episode)
class EpisodeAdmin(AdminActionMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "status_display",
        "publish_date",
        "duration_seconds",
        "article_count",
        "segment_count",
        "audio_status",
        "publish_status",
        "pipeline_link",
        "created_at",
    )
    list_filter = ("status", "language")
    search_fields = ("title", "description", "summary")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "article_count",
        "segment_count",
        "audio_status",
        "publish_status",
    )
    inlines = (EpisodeArticleInline,)
    date_hierarchy = "publish_date"
    actions = (
        "generate_script",
        "generate_audio",
        "publish_episode",
        "retry_failed_pipeline",
        "cancel_running_jobs",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Episode]:
        qs: QuerySet[Episode] = super().get_queryset(request)
        return qs.annotate(
            _article_count=Count("articles", distinct=True),
            _segment_count=Count("scripts__segments", distinct=True),
        )

    @admin.display(description="Status")
    def status_display(self, obj: Episode) -> str:
        return status_badge(obj.status)

    @admin.display(description="Articles")
    def article_count(self, obj: Episode) -> int:
        return getattr(obj, "_article_count", obj.articles.count())

    @admin.display(description="Segments")
    def segment_count(self, obj: Episode) -> int:
        return getattr(obj, "_segment_count", 0)

    @admin.display(description="Audio Status")
    def audio_status(self, obj: Episode) -> str:
        asset = obj.audio_assets.filter(is_final_episode_audio=True).first()
        if asset:
            return status_badge(asset.status)
        return status_badge("pending")

    @admin.display(description="Publish Status")
    def publish_status(self, obj: Episode) -> str:
        latest = obj.publish_jobs.order_by("-created_at").first()
        if latest:
            return status_badge(latest.status)
        return status_badge("pending")

    @admin.display(description="Pipeline")
    def pipeline_link(self, obj: Episode) -> str:
        url = reverse("operations:episode_pipeline", args=[obj.pk])
        return format_html('<a href="{}">View Pipeline</a>', url)

    @admin.action(description="Generate script for selected episodes")
    def generate_script(
        self,
        request: HttpRequest,
        queryset: QuerySet[Episode],
    ) -> None:
        job_ids = [
            str(self.dispatch_service.generate_script(str(ep.id)).id) for ep in queryset
        ]
        self.action_logger.log(
            action="generate_script",
            user_id=self._user_id(request),
            resource_type="episode",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Script generation queued.")

    @admin.action(description="Generate audio for selected episodes")
    def generate_audio(
        self,
        request: HttpRequest,
        queryset: QuerySet[Episode],
    ) -> None:
        job_ids = [
            str(self.dispatch_service.generate_audio(str(ep.id)).id) for ep in queryset
        ]
        self._message_jobs(request, job_ids, detail="Audio generation queued.")

    @admin.action(description="Publish selected episodes")
    def publish_episode(
        self,
        request: HttpRequest,
        queryset: QuerySet[Episode],
    ) -> None:
        job_ids = [
            str(self.dispatch_service.publish_episode(str(ep.id)).id) for ep in queryset
        ]
        self.action_logger.log(
            action="publish_episode",
            user_id=self._user_id(request),
            resource_type="episode",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Publishing queued.")

    @admin.action(description="Retry failed pipeline jobs")
    def retry_failed_pipeline(
        self,
        request: HttpRequest,
        queryset: QuerySet[Episode],
    ) -> None:
        job_ids: list[str] = []
        for episode in queryset:
            failed = Job.objects.filter(
                payload__episode_id=str(episode.id),
                status=JobStatus.FAILED,
            )
            for job in failed:
                retried = self.dispatch_service.retry_job(job)
                job_ids.append(str(retried.id))
        self._message_jobs(request, job_ids, detail="Failed jobs retried.")

    @admin.action(description="Cancel running jobs for selected episodes")
    def cancel_running_jobs(
        self,
        request: HttpRequest,
        queryset: QuerySet[Episode],
    ) -> None:
        cancelled = 0
        for episode in queryset:
            running = Job.objects.filter(
                payload__episode_id=str(episode.id),
                status__in=[JobStatus.RUNNING, JobStatus.QUEUED, JobStatus.RETRYING],
            )
            for job in running:
                self.dispatch_service.cancel_job(job)
                cancelled += 1
        self.message_user(request, f"Cancelled {cancelled} job(s).")


@admin.register(EpisodeArticle)
class EpisodeArticleAdmin(admin.ModelAdmin):
    list_display = ("episode", "article")
    list_filter = ("episode__status",)
    search_fields = ("episode__title", "article__title")
    autocomplete_fields = ("episode", "article")
