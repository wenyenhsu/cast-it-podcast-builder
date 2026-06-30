"""Episode status synchronization for workflow runs."""

from apps.episodes.models import Episode, EpisodeStatus
from domain.workflow.enums import WorkflowStepType

STEP_EPISODE_STATUS: dict[str, str] = {
    WorkflowStepType.PLAN_EPISODE: EpisodeStatus.DRAFT,
    WorkflowStepType.GENERATE_SCRIPT: EpisodeStatus.GENERATING_SCRIPT,
    WorkflowStepType.GENERATE_AUDIO: EpisodeStatus.GENERATING_AUDIO,
    WorkflowStepType.PROCESS_AUDIO: EpisodeStatus.COMPLETED,
    WorkflowStepType.PUBLISH_EPISODE: EpisodeStatus.PUBLISHING,
}


class EpisodeWorkflowSync:
    """Updates episode records based on workflow progress."""

    def attach_episode(self, episode_id: str, *, workflow_run_id: str) -> Episode:
        episode = Episode.objects.get(pk=episode_id)
        episode.status = EpisodeStatus.COLLECTING
        episode.save(update_fields=["status", "updated_at"])
        return episode

    def on_step_started(self, episode: Episode | None, step_type: str) -> None:
        if episode is None:
            return
        status = STEP_EPISODE_STATUS.get(step_type)
        if status:
            episode.status = status
            episode.save(update_fields=["status", "updated_at"])

    def on_workflow_succeeded(self, episode: Episode | None) -> None:
        if episode is None:
            return
        if episode.status != EpisodeStatus.COMPLETED:
            episode.status = EpisodeStatus.COMPLETED
            episode.save(update_fields=["status", "updated_at"])

    def on_workflow_failed(self, episode: Episode | None) -> None:
        if episode is None:
            return
        episode.status = EpisodeStatus.FAILED
        episode.save(update_fields=["status", "updated_at"])
