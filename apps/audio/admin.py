"""Admin configuration for audio app."""

from django.contrib import admin

from apps.audio.models import AudioAsset


@admin.register(AudioAsset)
class AudioAssetAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "script_segment",
        "provider",
        "status",
        "duration",
        "file_size",
        "created_at",
    )
    list_filter = ("status", "provider")
    search_fields = ("episode__title", "file_path", "checksum")
    readonly_fields = ("id", "created_at", "updated_at")
    autocomplete_fields = ("episode", "script_segment")
