"""Admin configuration for scripts app."""

from django.contrib import admin

from apps.scripts.models import Script, ScriptSegment


class ScriptSegmentInline(admin.TabularInline):
    model = ScriptSegment
    extra = 1
    ordering = ("sequence",)


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "version",
        "status",
        "llm_provider",
        "prompt_version",
        "created_at",
    )
    list_filter = ("status", "llm_provider")
    search_fields = ("episode__title", "llm_provider", "prompt_version")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("episode",)
    inlines = (ScriptSegmentInline,)


@admin.register(ScriptSegment)
class ScriptSegmentAdmin(admin.ModelAdmin):
    list_display = (
        "script",
        "sequence",
        "speaker",
        "voice",
        "emotion",
        "duration_seconds",
    )
    list_filter = ("speaker", "emotion")
    search_fields = ("text", "script__episode__title")
    readonly_fields = ("id",)
    autocomplete_fields = ("script",)
    ordering = ("script", "sequence")
