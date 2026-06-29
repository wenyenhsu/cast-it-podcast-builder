"""Admin configuration for audio app."""

from django.contrib import admin

from apps.audio.models import AudioAsset, PersonaVoiceMapping, VoiceProfile


@admin.register(VoiceProfile)
class VoiceProfileAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "provider",
        "provider_voice_id",
        "language",
        "gender",
        "default_speed",
        "enabled",
    )
    list_filter = ("provider", "enabled", "language")
    search_fields = ("name", "provider_voice_id", "description")


@admin.register(PersonaVoiceMapping)
class PersonaVoiceMappingAdmin(admin.ModelAdmin):
    list_display = ("persona", "voice_profile", "provider", "enabled")
    list_filter = ("persona", "provider", "enabled")
    autocomplete_fields = ("voice_profile",)


@admin.register(AudioAsset)
class AudioAssetAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "script_segment",
        "provider",
        "voice",
        "status",
        "duration",
        "format",
        "file_size",
        "created_at",
    )
    list_filter = ("status", "provider", "format")
    search_fields = ("episode__title", "file_path", "checksum", "voice")
    readonly_fields = ("id", "created_at", "updated_at", "generated_at")
    autocomplete_fields = ("episode", "script_segment")
