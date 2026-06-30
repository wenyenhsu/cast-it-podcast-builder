"""Workflow step adapter registry."""

from services.workflow.adapters.base import WorkflowStepAdapter
from services.workflow.adapters.implementations import (
    DefaultClassifyArticlesAdapter,
    DefaultCollectArticlesAdapter,
    DefaultGenerateAudioAdapter,
    DefaultGenerateScriptAdapter,
    DefaultIndexKnowledgeAdapter,
    DefaultPlanEpisodeAdapter,
    DefaultProcessAudioAdapter,
    DefaultPublishEpisodeAdapter,
    DefaultRankArticlesAdapter,
    DefaultSummarizeArticlesAdapter,
)


def build_default_adapter_registry() -> dict[str, WorkflowStepAdapter]:
    """Return the default step-type to adapter mapping."""
    adapters: list[WorkflowStepAdapter] = [
        DefaultIndexKnowledgeAdapter(),
        DefaultCollectArticlesAdapter(),
        DefaultSummarizeArticlesAdapter(),
        DefaultClassifyArticlesAdapter(),
        DefaultRankArticlesAdapter(),
        DefaultPlanEpisodeAdapter(),
        DefaultGenerateScriptAdapter(),
        DefaultGenerateAudioAdapter(),
        DefaultProcessAudioAdapter(),
        DefaultPublishEpisodeAdapter(),
    ]
    return {adapter.step_type: adapter for adapter in adapters}
