"""Admin configuration for episodes app."""

from django.contrib import admin

from apps.episodes.models import Episode, EpisodeArticle


class EpisodeArticleInline(admin.TabularInline):
    model = EpisodeArticle
    extra = 1
    autocomplete_fields = ("article",)


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "status",
        "language",
        "publish_date",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("status", "language")
    search_fields = ("title", "description", "summary")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (EpisodeArticleInline,)
    date_hierarchy = "publish_date"


@admin.register(EpisodeArticle)
class EpisodeArticleAdmin(admin.ModelAdmin):
    list_display = ("episode", "article")
    list_filter = ("episode__status",)
    search_fields = ("episode__title", "article__title")
    autocomplete_fields = ("episode", "article")
