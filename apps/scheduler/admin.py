"""Admin configuration for scheduler app."""

from django.contrib import admin

from apps.scheduler.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "status",
        "progress",
        "retry_count",
        "celery_task_id",
        "started_at",
        "completed_at",
        "created_at",
    )
    list_filter = ("job_type", "status")
    search_fields = ("error_message", "celery_task_id")
    readonly_fields = ("id", "created_at", "updated_at")
    date_hierarchy = "created_at"
