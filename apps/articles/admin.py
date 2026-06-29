"""Admin configuration for articles app."""

from django.contrib import admin

from apps.articles.models import Article, ArticleTag, Tag


class ArticleTagInline(admin.TabularInline):
    model = ArticleTag
    extra = 1
    autocomplete_fields = ("tag",)


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "source",
        "status",
        "language",
        "category",
        "importance_score",
        "published_at",
        "created_at",
    )
    list_filter = ("status", "language", "category", "source")
    search_fields = ("title", "author", "url", "content_hash", "summary", "content")
    readonly_fields = (
        "id",
        "content_hash",
        "summary_generated_at",
        "classified_at",
        "keywords_generated_at",
        "created_at",
        "updated_at",
    )
    autocomplete_fields = ("source",)
    inlines = (ArticleTagInline,)
    date_hierarchy = "published_at"
    ordering = ("-published_at", "-created_at")
    list_per_page = 50
    list_select_related = ("source",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("id",)
    ordering = ("name",)


@admin.register(ArticleTag)
class ArticleTagAdmin(admin.ModelAdmin):
    list_display = ("article", "tag")
    list_filter = ("tag",)
    search_fields = ("article__title", "tag__name")
    autocomplete_fields = ("article", "tag")
