"""Admin configuration for publish app."""

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest

from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin
from apps.publish.models import PublishedEpisode, PublishJob


@admin.register(PublishJob)
class PublishJobAdmin(AdminActionMixin, admin.ModelAdmin):
    list_display = (
        "episode",
        "platform",
        "status_display",
        "published_url",
        "started_at",
        "completed_at",
    )
    list_filter = ("platform", "status")
    search_fields = (
        "episode__title",
        "published_url",
        "external_id",
        "error_message",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "error_message",
    )
    autocomplete_fields = ("episode",)
    date_hierarchy = "started_at"
    actions = ("retry_publish", "cancel_publish", "republish")

    @admin.display(description="Status")
    def status_display(self, obj: PublishJob) -> str:
        return status_badge(obj.status)

    @admin.action(description="Retry failed publish jobs")
    def retry_publish(
        self,
        request: HttpRequest,
        queryset: QuerySet[PublishJob],
    ) -> None:
        retried = self.action_service.retry_publish_jobs(
            [str(job.id) for job in queryset],
            user_id=self._user_id(request),
        )
        self.message_user(request, f"Retried {len(retried)} publish job(s).")

    @admin.action(description="Cancel selected publish jobs")
    def cancel_publish(
        self,
        request: HttpRequest,
        queryset: QuerySet[PublishJob],
    ) -> None:
        cancelled = self.action_service.cancel_publish_jobs(
            [str(job.id) for job in queryset],
            user_id=self._user_id(request),
        )
        self.message_user(request, f"Cancelled {cancelled} publish job(s).")

    @admin.action(description="Republish selected episodes")
    def republish(
        self,
        request: HttpRequest,
        queryset: QuerySet[PublishJob],
    ) -> None:
        job_ids: list[str] = []
        seen: set[str] = set()
        for publish_job in queryset:
            episode_id = str(publish_job.episode_id)
            if episode_id in seen:
                continue
            seen.add(episode_id)
            job = self.dispatch_service.publish_episode(
                episode_id,
                platforms=[publish_job.platform],
            )
            job_ids.append(str(job.id))
        self.action_logger.log(
            action="republish",
            user_id=self._user_id(request),
            resource_type="publish_job",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Republish queued.")


@admin.register(PublishedEpisode)
class PublishedEpisodeAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "platform",
        "published_url",
        "external_id",
        "published_at",
    )
    list_filter = ("platform",)
    search_fields = ("episode__title", "published_url", "external_id")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("episode",)
    date_hierarchy = "published_at"
