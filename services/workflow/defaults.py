"""Default workflow definitions."""

from apps.workflow.models import WorkflowDefinition, WorkflowStep
from domain.workflow.enums import WorkflowStepType

PODCAST_PRODUCTION_WORKFLOW = "podcast_production"


def ensure_default_workflow_definition() -> WorkflowDefinition:
    """Create the default podcast production workflow if missing."""
    definition, created = WorkflowDefinition.objects.get_or_create(
        name=PODCAST_PRODUCTION_WORKFLOW,
        version=1,
        defaults={
            "description": (
                "End-to-end podcast production pipeline from article collection "
                "through publishing."
            ),
            "is_active": True,
        },
    )
    if created or not definition.steps.exists():
        _create_default_steps(definition)
    return definition


def _create_default_steps(definition: WorkflowDefinition) -> None:
    steps = [
        (1, "Index Knowledge", WorkflowStepType.INDEX_KNOWLEDGE, {"optional": True}),
        (2, "Collect Articles", WorkflowStepType.COLLECT_ARTICLES, {}),
        (3, "Summarize Articles", WorkflowStepType.SUMMARIZE_ARTICLES, {}),
        (4, "Classify Articles", WorkflowStepType.CLASSIFY_ARTICLES, {}),
        (5, "Rank Articles", WorkflowStepType.RANK_ARTICLES, {}),
        (6, "Plan Episode", WorkflowStepType.PLAN_EPISODE, {}),
        (7, "Generate Script", WorkflowStepType.GENERATE_SCRIPT, {}),
        (8, "Generate Audio", WorkflowStepType.GENERATE_AUDIO, {}),
        (9, "Process Audio", WorkflowStepType.PROCESS_AUDIO, {}),
        (10, "Publish Episode", WorkflowStepType.PUBLISH_EPISODE, {}),
    ]
    for sequence, name, step_type, config in steps:
        WorkflowStep.objects.get_or_create(
            workflow_definition=definition,
            sequence=sequence,
            defaults={
                "name": name,
                "step_type": step_type,
                "timeout_seconds": 3600,
                "retry_limit": 3,
                "config": {**config, "enabled": True},
            },
        )
