"""Admin configuration for scripts app."""

from django.contrib import admin

from apps.scripts.models import Script, ScriptMetadata, ScriptSegment


class ScriptSegmentInline(admin.TabularInline):
    model = ScriptSegment
    extra = 0
    ordering = ("sequence",)
    readonly_fields = ("id",)


class ScriptMetadataInline(admin.StackedInline):
    model = ScriptMetadata
    extra = 0
    readonly_fields = ("id",)


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "version",
        "title",
        "status",
        "validation_status",
        "llm_provider",
        "model_name",
        "prompt_version",
        "estimated_duration_seconds",
        "generated_at",
    )
    list_filter = ("status", "validation_status", "llm_provider")
    search_fields = ("title", "episode__title", "llm_provider", "prompt_version")
    readonly_fields = ("id", "created_at", "updated_at", "generated_at")
    autocomplete_fields = ("episode",)
    inlines = (ScriptMetadataInline, ScriptSegmentInline)


@admin.register(ScriptSegment)
class ScriptSegmentAdmin(admin.ModelAdmin):
    list_display = (
        "script",
        "sequence",
        "speaker",
        "voice",
        "emotion",
        "estimated_duration_seconds",
    )
    list_filter = ("speaker", "emotion")
    search_fields = ("text", "script__episode__title", "script__title")
    readonly_fields = ("id",)
    autocomplete_fields = ("script",)
    ordering = ("script", "sequence")


@admin.register(ScriptMetadata)
class ScriptMetadataAdmin(admin.ModelAdmin):
    list_display = ("script", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("script__title", "script__episode__title")
    readonly_fields = ("id", "created_at", "updated_at")
