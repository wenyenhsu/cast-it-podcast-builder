"""Admin configuration for publish app."""

from django.contrib import admin

from apps.publish.models import PublishJob


@admin.register(PublishJob)
class PublishJobAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "platform",
        "status",
        "published_url",
        "started_at",
        "completed_at",
    )
    list_filter = ("platform", "status")
    search_fields = ("episode__title", "published_url", "error_message")
    readonly_fields = ("id",)
    autocomplete_fields = ("episode",)
    date_hierarchy = "started_at"
