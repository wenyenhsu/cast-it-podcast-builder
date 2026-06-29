"""Admin configuration for scheduler app."""

from django.contrib import admin

from apps.scheduler.models import Job


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "job_type",
        "status",
        "progress",
        "started_at",
        "completed_at",
    )
    list_filter = ("job_type", "status")
    search_fields = ("error",)
    readonly_fields = ("id",)
    date_hierarchy = "started_at"
