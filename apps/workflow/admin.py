"""Admin configuration for workflow app."""

from django.contrib import admin

from apps.workflow.models import (
    WorkflowDefinition,
    WorkflowRun,
    WorkflowStep,
    WorkflowStepRun,
)


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0
    ordering = ("sequence",)
    readonly_fields = ("id",)


class WorkflowStepRunInline(admin.TabularInline):
    model = WorkflowStepRun
    extra = 0
    readonly_fields = ("id", "status", "progress", "started_at", "completed_at")
    ordering = ("workflow_step__sequence",)


@admin.register(WorkflowDefinition)
class WorkflowDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    inlines = (WorkflowStepInline,)


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = (
        "workflow_definition",
        "episode",
        "status",
        "current_step",
        "progress",
        "retry_count",
        "started_at",
    )
    list_filter = ("status", "workflow_definition")
    search_fields = ("current_step", "error_message")
    readonly_fields = ("id", "created_at", "updated_at", "result")
    inlines = (WorkflowStepRunInline,)
    autocomplete_fields = ("episode", "workflow_definition")


@admin.register(WorkflowStepRun)
class WorkflowStepRunAdmin(admin.ModelAdmin):
    list_display = (
        "workflow_run",
        "workflow_step",
        "status",
        "progress",
        "retry_count",
        "started_at",
    )
    list_filter = ("status",)
    readonly_fields = ("id", "created_at", "updated_at")
