"""Admin configuration for knowledge base app."""

from django.contrib import admin

from apps.knowledge.models import KnowledgeChunk, KnowledgeDocument


class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    extra = 0
    readonly_fields = ("id", "sequence", "token_count", "embedding_status")
    fields = ("sequence", "text", "token_count", "embedding_status")
    ordering = ("sequence",)


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "source_type",
        "source_id",
        "language",
        "checksum",
        "created_at",
        "updated_at",
    )
    list_filter = ("source_type", "language")
    search_fields = ("title", "content", "source_id", "checksum")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = (KnowledgeChunkInline,)


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = (
        "document",
        "sequence",
        "token_count",
        "embedding_status",
        "created_at",
    )
    list_filter = ("embedding_status",)
    search_fields = ("text", "document__title")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("document",)
