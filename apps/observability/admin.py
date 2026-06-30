"""Observability admin registration."""

from django.contrib import admin

from apps.observability.models import OperationalEvent


@admin.register(OperationalEvent)
class OperationalEventAdmin(admin.ModelAdmin):
    """Read-only admin for operational events."""

    list_display = (
        "created_at",
        "severity",
        "event_type",
        "name",
        "source",
        "correlation_id",
    )
    list_filter = ("severity", "event_type", "source")
    search_fields = ("name", "message", "correlation_id", "job_id")
    readonly_fields = [field.name for field in OperationalEvent._meta.fields]

    def has_add_permission(self, request) -> bool:
        del request
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        del request, obj
        return False
