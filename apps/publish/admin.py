"""Admin configuration for publish app."""

from django.contrib import admin

from apps.publish.models import PublishedEpisode, PublishJob


@admin.register(PublishJob)
class PublishJobAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "platform",
        "status",
        "published_url",
        "external_id",
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
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("episode",)
    date_hierarchy = "started_at"


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
