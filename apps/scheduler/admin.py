"""Admin configuration for scheduler app."""

import json

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin, AdminRolePermissionMixin
from apps.scheduler.models import Job, JobStatus


@admin.register(Job)
class JobAdmin(AdminRolePermissionMixin, AdminActionMixin, admin.ModelAdmin):
    operator_only_actions = ("delete_completed_jobs", "cancel_jobs")
    list_display = (
        "job_type",
        "status_display",
        "progress_bar",
        "retry_count",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = ("job_type", "status")
    search_fields = ("error_message", "celery_task_id", "payload", "result")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "payload_display",
        "result_display",
        "error_message",
        "job_actions",
    )
    date_hierarchy = "created_at"
    change_form_template = "admin/scheduler/job/change_form.html"
    actions = ("retry_failed_jobs", "cancel_jobs", "delete_completed_jobs")

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "job_type",
                    "status",
                    "progress",
                    "retry_count",
                    "celery_task_id",
                    "started_at",
                    "completed_at",
                    "job_actions",
                ),
            },
        ),
        (
            "Payload & Result",
            {
                "classes": ("collapse",),
                "fields": ("payload_display", "result_display", "error_message"),
            },
        ),
        (
            "Timestamps",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "updated_at"),
            },
        ),
    )

    def get_urls(self) -> list:
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/retry/",
                self.admin_site.admin_view(self.retry_job_view),
                name="scheduler_job_retry",
            ),
            path(
                "<path:object_id>/cancel/",
                self.admin_site.admin_view(self.cancel_job_view),
                name="scheduler_job_cancel",
            ),
        ]
        return custom_urls + urls

    @admin.display(description="Status")
    def status_display(self, obj: Job) -> str:
        return status_badge(obj.status)

    @admin.display(description="Progress")
    def progress_bar(self, obj: Job) -> str:
        return format_html(
            '<div class="ops-progress-bar">'
            '<div class="ops-progress-fill" style="width: {}%;"></div>'
            "<span>{}%</span></div>",
            obj.progress,
            obj.progress,
        )

    @admin.display(description="Actions")
    def job_actions(self, obj: Job) -> str:
        if obj.pk is None:
            return "—"
        retry_url = reverse("admin:scheduler_job_retry", args=[obj.pk])
        cancel_url = reverse("admin:scheduler_job_cancel", args=[obj.pk])
        buttons: list[str] = []
        if obj.status in {JobStatus.FAILED, JobStatus.CANCELLED}:
            buttons.append(f'<a class="button" href="{retry_url}">Retry</a>')
        if obj.status in {
            JobStatus.PENDING,
            JobStatus.QUEUED,
            JobStatus.RUNNING,
            JobStatus.RETRYING,
        }:
            buttons.append(f'<a class="button" href="{cancel_url}">Cancel</a>')
        return format_html(" ".join(buttons)) if buttons else "—"

    @admin.display(description="Payload")
    def payload_display(self, obj: Job) -> str:
        return format_html(
            "<pre>{}</pre>",
            json.dumps(obj.payload or {}, indent=2),
        )

    @admin.display(description="Result")
    def result_display(self, obj: Job) -> str:
        return format_html(
            "<pre>{}</pre>",
            json.dumps(obj.result or {}, indent=2),
        )

    def retry_job_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> HttpResponseRedirect:
        job = Job.objects.get(pk=object_id)
        retried = self.dispatch_service.retry_job(job)
        self.action_logger.log(
            action="retry_job",
            user_id=self._user_id(request),
            resource_type="job",
            resource_ids=[str(job.id)],
            extra={"retried_job_id": str(retried.id)},
        )
        self.message_user(request, f"Job retried as {retried.id}.")
        return HttpResponseRedirect(
            reverse("admin:scheduler_job_change", args=[retried.pk])
        )

    def cancel_job_view(
        self,
        request: HttpRequest,
        object_id: str,
    ) -> HttpResponseRedirect:
        job = Job.objects.get(pk=object_id)
        self.dispatch_service.cancel_job(job)
        self.action_logger.log(
            action="cancel_job",
            user_id=self._user_id(request),
            resource_type="job",
            resource_ids=[str(job.id)],
        )
        self.message_user(request, f"Job {job.id} cancelled.")
        return HttpResponseRedirect(
            reverse("admin:scheduler_job_change", args=[job.pk]),
        )

    @admin.action(description="Retry failed jobs")
    def retry_failed_jobs(
        self,
        request: HttpRequest,
        queryset: QuerySet[Job],
    ) -> None:
        job_ids: list[str] = []
        for job in queryset.filter(status=JobStatus.FAILED):
            retried = self.dispatch_service.retry_job(job)
            job_ids.append(str(retried.id))
        self._message_jobs(request, job_ids, detail="Failed jobs retried.")

    @admin.action(description="Cancel selected jobs")
    def cancel_jobs(
        self,
        request: HttpRequest,
        queryset: QuerySet[Job],
    ) -> None:
        cancelled = 0
        for job in queryset.filter(
            status__in=[
                JobStatus.PENDING,
                JobStatus.QUEUED,
                JobStatus.RUNNING,
                JobStatus.RETRYING,
            ]
        ):
            self.dispatch_service.cancel_job(job)
            cancelled += 1
        self.action_logger.log(
            action="cancel_jobs",
            user_id=self._user_id(request),
            resource_type="job",
            resource_ids=self._selected_ids(queryset),
        )
        self.message_user(request, f"Cancelled {cancelled} job(s).")

    @admin.action(description="Delete completed jobs")
    def delete_completed_jobs(
        self,
        request: HttpRequest,
        queryset: QuerySet[Job],
    ) -> None:
        completed = queryset.filter(status=JobStatus.SUCCEEDED)
        count = completed.count()
        ids = self._selected_ids(completed)
        completed.delete()
        self.action_logger.log(
            action="delete_completed_jobs",
            user_id=self._user_id(request),
            resource_type="job",
            resource_ids=ids,
        )
        self.message_user(request, f"Deleted {count} completed job(s).")
