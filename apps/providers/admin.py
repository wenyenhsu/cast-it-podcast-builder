"""Admin configuration for providers app."""

from django.contrib import admin
from django.db.models import QuerySet

from apps.providers.models import NewsSource


@admin.register(NewsSource)
class NewsSourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider_type",
        "language",
        "enabled",
        "rss_url",
        "created_at",
    )
    list_filter = ("provider_type", "language", "enabled")
    search_fields = ("name", "homepage", "rss_url")
    list_editable = ("enabled",)
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("name",)
    list_per_page = 25
    actions = ("enable_sources", "disable_sources")

    @admin.action(description="Enable selected news sources")
    def enable_sources(
        self,
        request: object,
        queryset: QuerySet[NewsSource],
    ) -> None:
        queryset.update(enabled=True)

    @admin.action(description="Disable selected news sources")
    def disable_sources(
        self,
        request: object,
        queryset: QuerySet[NewsSource],
    ) -> None:
        queryset.update(enabled=False)
