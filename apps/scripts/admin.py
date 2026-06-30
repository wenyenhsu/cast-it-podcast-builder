"""Admin configuration for scripts app."""

import json

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse

from api.v1.services.script_validation import validate_stored_script
from apps.core.admin.badges import status_badge
from apps.core.admin.mixins import AdminActionMixin
from apps.scripts.models import Script, ScriptMetadata, ScriptSegment, ValidationStatus


class ScriptSegmentInline(admin.TabularInline):
    model = ScriptSegment
    extra = 0
    ordering = ("sequence",)
    readonly_fields = ("id", "text_preview")
    fields = (
        "sequence",
        "speaker",
        "voice",
        "emotion",
        "text_preview",
        "estimated_duration_seconds",
    )

    @admin.display(description="Text Preview")
    def text_preview(self, obj: ScriptSegment) -> str:
        text = obj.text[:120] + "..." if len(obj.text) > 120 else obj.text
        return text


class ScriptMetadataInline(admin.StackedInline):
    model = ScriptMetadata
    extra = 0
    readonly_fields = ("id",)
    classes = ("collapse",)


@admin.register(Script)
class ScriptAdmin(AdminActionMixin, admin.ModelAdmin):
    list_display = (
        "episode",
        "version",
        "status_display",
        "validation_display",
        "prompt_version",
        "llm_provider",
        "model_name",
        "generation_time_display",
        "estimated_duration_seconds",
        "generated_at",
    )
    list_filter = ("status", "validation_status", "llm_provider")
    search_fields = ("title", "episode__title", "llm_provider", "prompt_version")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "generated_at",
        "generation_time_display",
    )
    autocomplete_fields = ("episode",)
    inlines = (ScriptMetadataInline, ScriptSegmentInline)
    actions = ("regenerate_script", "validate_script", "export_json")

    @admin.display(description="Status")
    def status_display(self, obj: Script) -> str:
        return status_badge(obj.status)

    @admin.display(description="Validation")
    def validation_display(self, obj: Script) -> str:
        return status_badge(obj.validation_status)

    @admin.display(description="Generation Time")
    def generation_time_display(self, obj: Script) -> str:
        metadata = getattr(obj, "metadata", None)
        if metadata and metadata.token_usage:
            elapsed = metadata.token_usage.get("generation_time_seconds")
            if elapsed is not None:
                return f"{elapsed}s"
        if obj.generated_at:
            return str(obj.generated_at)
        return "—"

    @admin.action(description="Regenerate script for selected episodes")
    def regenerate_script(
        self,
        request: HttpRequest,
        queryset: QuerySet[Script],
    ) -> None:
        job_ids: list[str] = []
        episode_ids: set[str] = set()
        for script in queryset:
            episode_id = str(script.episode_id)
            if episode_id in episode_ids:
                continue
            episode_ids.add(episode_id)
            job = self.dispatch_service.generate_script(
                episode_id,
                script_id=str(script.id),
            )
            job_ids.append(str(job.id))
        self.action_logger.log(
            action="regenerate_script",
            user_id=self._user_id(request),
            resource_type="script",
            resource_ids=self._selected_ids(queryset),
        )
        self._message_jobs(request, job_ids, detail="Script regeneration queued.")

    @admin.action(description="Validate selected scripts")
    def validate_script(
        self,
        request: HttpRequest,
        queryset: QuerySet[Script],
    ) -> None:
        passed = 0
        failed = 0
        for script in queryset:
            result = validate_stored_script(script)
            script.validation_status = (
                ValidationStatus.PASSED if result.passed else ValidationStatus.FAILED
            )
            script.save(update_fields=["validation_status", "updated_at"])
            if result.passed:
                passed += 1
            else:
                failed += 1
        self.action_logger.log(
            action="validate_script",
            user_id=self._user_id(request),
            resource_type="script",
            resource_ids=self._selected_ids(queryset),
            extra={"passed": passed, "failed": failed},
        )
        self.message_user(
            request,
            f"Validation complete: {passed} passed, {failed} failed.",
        )

    @admin.action(description="Export selected scripts as JSON")
    def export_json(
        self,
        request: HttpRequest,
        queryset: QuerySet[Script],
    ) -> HttpResponse:
        if queryset.count() == 1:
            script = queryset.first()
            assert script is not None
            payload = self.action_service.export_script_json(script)
            response = HttpResponse(payload, content_type="application/json")
            response["Content-Disposition"] = (
                f'attachment; filename="script-{script.id}.json"'
            )
            return response
        combined = [
            json.loads(self.action_service.export_script_json(script))
            for script in queryset
        ]
        payload = json.dumps(combined, indent=2)
        response = HttpResponse(payload, content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="scripts.json"'
        self.action_logger.log(
            action="export_script_json",
            user_id=self._user_id(request),
            resource_type="script",
            resource_ids=self._selected_ids(queryset),
        )
        return response


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
