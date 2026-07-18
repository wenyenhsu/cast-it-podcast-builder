"""Admin configuration for articles app."""

from django.contrib import admin
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html

from apps.articles.models import Article, ArticleTag, Tag
from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin


class ArticleTagInline(admin.TabularInline):
    model = ArticleTag
    extra = 1
    autocomplete_fields = ("tag",)


@admin.register(Article)
class ArticleAdmin(AdminActionMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "source",
        "status_display",
        "script_source_status",
        "live_status",
        "category",
        "importance_score",
        "published_at",
        "created_at",
    )
    list_filter = (
        "selected_for_script",
        "status",
        "language",
        "category",
        "source",
    )
    search_fields = ("title", "author", "url", "content_hash", "summary", "content")
    readonly_fields = (
        "id",
        "content_hash",
        "summary",
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
    actions = (
        "resummarize_selected",
        "reclassify_selected",
        "rescore_selected",
        "add_to_episode",
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[Article]:
        queryset: QuerySet[Article] = super().get_queryset(request)
        return queryset.annotate(
            _public_episode_count=Count(
                "episodes",
                filter=Q(episodes__publish=1),
                distinct=True,
            )
        )

    @admin.display(description="Status")
    def status_display(self, obj: Article) -> str:
        return status_badge(obj.status)

    @admin.display(description="Script Source", boolean=True)
    def script_source_status(self, obj: Article) -> bool:
        return obj.selected_for_script

    @admin.display(description="Live")
    def live_status(self, obj: Article) -> str:
        count = getattr(obj, "_public_episode_count", 0)
        if count:
            return format_html('<span style="color:#198754">Live ({})</span>', count)
        return format_html('<span style="color:#6c757d">Not live</span>')

    @admin.action(description="Re-summarize selected articles")
    def resummarize_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article],
    ) -> None:
        job_ids = [
            str(self.dispatch_service.summarize_article(str(article.id)).id)
            for article in queryset
        ]
        self.action_logger.log(
            action="re_summarize",
            user_id=self._user_id(request),
            resource_type="article",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Summarization queued.")

    @admin.action(description="Re-classify selected articles")
    def reclassify_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article],
    ) -> None:
        job_ids = [
            str(self.dispatch_service.classify_article(str(article.id)).id)
            for article in queryset
        ]
        self.action_logger.log(
            action="re_classify",
            user_id=self._user_id(request),
            resource_type="article",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Classification queued.")

    @admin.action(description="Re-score selected articles")
    def rescore_selected(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article],
    ) -> None:
        count = self.action_service.rescore_articles(
            queryset,
            user_id=self._user_id(request),
        )
        self.message_user(request, f"Rescored {count} article(s).")

    @admin.action(description="Add selected articles to draft episode")
    def add_to_episode(
        self,
        request: HttpRequest,
        queryset: QuerySet[Article],
    ) -> None:
        episode_id = self.action_service.add_articles_to_draft_episode(
            queryset,
            user_id=self._user_id(request),
        )
        if episode_id:
            self.message_user(
                request,
                f"Added articles to episode {episode_id}.",
            )
        else:
            self.message_user(
                request,
                "No draft episode found. Create an episode first.",
                level="warning",
            )


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
