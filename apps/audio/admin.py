"""Admin configuration for audio app."""

from django.conf import settings
from django.contrib import admin
from django.db.models import QuerySet
from django.http import FileResponse, HttpRequest, HttpResponse

from apps.audio.models import (
    AudioAsset,
    PersonaVoiceMapping,
    PipelineRun,
    VoiceProfile,
)
from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin


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
    ordering = ("provider", "name")


@admin.register(PersonaVoiceMapping)
class PersonaVoiceMappingAdmin(admin.ModelAdmin):
    list_display = ("persona", "voice_profile", "provider", "enabled")
    list_filter = ("persona", "provider", "enabled")
    autocomplete_fields = ("voice_profile",)
    ordering = ("provider", "persona")


@admin.register(AudioAsset)
class AudioAssetAdmin(AdminActionMixin, admin.ModelAdmin):
    list_display = (
        "episode",
        "provider",
        "voice",
        "status_display",
        "duration",
        "format",
        "file_size_display",
        "is_final_episode_audio",
        "generated_at",
    )
    list_filter = ("status", "provider", "format", "is_final_episode_audio")
    search_fields = ("episode__title", "file_path", "checksum", "voice")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "generated_at",
        "file_size_display",
    )
    autocomplete_fields = ("episode", "script_segment")
    actions = (
        "regenerate_audio",
        "run_audio_pipeline",
        "download_audio",
        "delete_generated_audio",
    )

    @admin.display(description="Status")
    def status_display(self, obj: AudioAsset) -> str:
        return status_badge(obj.status)

    @admin.display(description="File Size")
    def file_size_display(self, obj: AudioAsset) -> str:
        if obj.file_size is None:
            return "—"
        if obj.file_size >= 1_048_576:
            return f"{obj.file_size / 1_048_576:.1f} MB"
        if obj.file_size >= 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        return f"{obj.file_size} B"

    @admin.action(description="Regenerate audio for selected assets")
    def regenerate_audio(
        self,
        request: HttpRequest,
        queryset: QuerySet[AudioAsset],
    ) -> None:
        job_ids: list[str] = []
        seen_episodes: set[str] = set()
        for asset in queryset:
            episode_id = str(asset.episode_id)
            job = self.dispatch_service.generate_audio(
                episode_id,
                audio_asset_id=str(asset.id),
            )
            job_ids.append(str(job.id))
            seen_episodes.add(episode_id)
        self.action_logger.log(
            action="regenerate_audio",
            user_id=self._user_id(request),
            resource_type="audio_asset",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Audio regeneration queued.")

    @admin.action(description="Run audio pipeline for selected assets")
    def run_audio_pipeline(
        self,
        request: HttpRequest,
        queryset: QuerySet[AudioAsset],
    ) -> None:
        job_ids: list[str] = []
        for asset in queryset:
            job = self.dispatch_service.run_audio_pipeline(
                str(asset.episode_id),
                audio_asset_id=str(asset.id),
            )
            job_ids.append(str(job.id))
        self._message_jobs(request, job_ids, detail="Audio pipeline queued.")

    @admin.action(description="Download selected audio files")
    def download_audio(
        self,
        request: HttpRequest,
        queryset: QuerySet[AudioAsset],
    ) -> HttpResponse | FileResponse | None:
        if queryset.count() != 1:
            self.message_user(
                request,
                "Select exactly one audio asset to download.",
                level="warning",
            )
            return None
        asset = queryset.first()
        assert asset is not None
        file_path = settings.MEDIA_ROOT / asset.file_path
        if not file_path.exists():
            self.message_user(request, "Audio file not found on disk.", level="error")
            return None
        self.action_logger.log(
            action="download_audio",
            user_id=self._user_id(request),
            resource_type="audio_asset",
            resource_ids=[str(asset.id)],
        )
        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=file_path.name,
        )

    @admin.action(description="Delete selected generated audio")
    def delete_generated_audio(
        self,
        request: HttpRequest,
        queryset: QuerySet[AudioAsset],
    ) -> None:
        count = self.action_service.delete_audio_assets(
            queryset,
            user_id=self._user_id(request),
        )
        self.message_user(request, f"Deleted {count} audio asset(s).")


@admin.register(PipelineRun)
class PipelineRunAdmin(admin.ModelAdmin):
    list_display = (
        "episode",
        "status_display",
        "audio_asset",
        "started_at",
        "completed_at",
        "output_path",
    )
    list_filter = ("status",)
    search_fields = ("episode__title", "output_path", "error_message")
    readonly_fields = ("id", "created_at", "updated_at", "error_message")
    autocomplete_fields = ("episode", "audio_asset")
    ordering = ("-created_at",)

    @admin.display(description="Status")
    def status_display(self, obj: PipelineRun) -> str:
        return status_badge(obj.status)
