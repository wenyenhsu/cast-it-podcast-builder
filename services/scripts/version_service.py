"""Script versioning service."""

import logging
import uuid

from django.db import transaction

from apps.scripts.models import Script, ScriptMetadata, ScriptSegment, ScriptStatus, ValidationStatus
from domain.scripts.exceptions import ScriptVersionConflictError

logger = logging.getLogger(__name__)

EpisodeId = uuid.UUID | str


class ScriptVersionService:
    """Manages script version creation and active script selection."""

    def get_next_version(self, episode_id: EpisodeId) -> int:
        """Return the next script version number for an episode."""
        latest = (
            Script.objects.filter(episode_id=episode_id)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        return (latest or 0) + 1

    def get_active_script(self, episode_id: EpisodeId) -> Script | None:
        """Return the currently active script for an episode, if any."""
        metadata = (
            ScriptMetadata.objects.filter(
                script__episode_id=episode_id,
                is_active=True,
            )
            .select_related("script")
            .first()
        )
        return metadata.script if metadata else None

    @transaction.atomic
    def create_version_placeholder(
        self,
        episode_id: EpisodeId,
        *,
        llm_provider: str,
        model_name: str,
        prompt_version: str,
    ) -> Script:
        """Create a generating script record before LLM completion."""
        version = self.get_next_version(episode_id)
        script = Script.objects.create(
            episode_id=episode_id,
            version=version,
            llm_provider=llm_provider,
            model_name=model_name,
            prompt_version=prompt_version,
            status=ScriptStatus.GENERATING,
            validation_status=ValidationStatus.PENDING,
        )
        ScriptMetadata.objects.create(
            script=script,
            is_active=False,
            source_article_ids=[],
            selected_topics=[],
        )
        logger.info(
            "Script version placeholder created",
            extra={
                "event": "script_version_created",
                "episode_id": str(episode_id),
                "script_id": str(script.id),
                "version": version,
            },
        )
        return script

    @transaction.atomic
    def reset_placeholder_for_retry(
        self,
        script: Script,
        *,
        llm_provider: str,
        model_name: str,
        prompt_version: str,
    ) -> Script:
        """Reset a failed or in-progress script for another generation attempt."""
        script.status = ScriptStatus.GENERATING
        script.validation_status = ValidationStatus.PENDING
        script.llm_provider = llm_provider
        script.model_name = model_name
        script.prompt_version = prompt_version
        script.title = ""
        script.estimated_duration_seconds = None
        script.generated_at = None
        script.save(
            update_fields=[
                "status",
                "validation_status",
                "llm_provider",
                "model_name",
                "prompt_version",
                "title",
                "estimated_duration_seconds",
                "generated_at",
                "updated_at",
            ]
        )
        ScriptSegment.objects.filter(script=script).delete()
        metadata = getattr(script, "metadata", None)
        if metadata is not None:
            metadata.source_article_ids = []
            metadata.selected_topics = []
            metadata.token_usage = {}
            metadata.validation_results = {}
            metadata.generation_notes = ""
            metadata.save(
                update_fields=[
                    "source_article_ids",
                    "selected_topics",
                    "token_usage",
                    "validation_results",
                    "generation_notes",
                    "updated_at",
                ]
            )
        logger.info(
            "Script placeholder reset for retry",
            extra={
                "event": "script_version_reset_for_retry",
                "script_id": str(script.id),
                "episode_id": str(script.episode_id),
                "version": script.version,
            },
        )
        return script

    @transaction.atomic
    def activate_script(self, script: Script) -> None:
        """Mark a script as the active version for its episode."""
        ScriptMetadata.objects.filter(
            script__episode_id=script.episode_id,
            is_active=True,
        ).update(is_active=False)

        metadata, _ = ScriptMetadata.objects.get_or_create(
            script=script,
            defaults={"is_active": True},
        )
        if not metadata.is_active:
            metadata.is_active = True
            metadata.save(update_fields=["is_active"])

        logger.info(
            "Script version activated",
            extra={
                "event": "script_version_activated",
                "script_id": str(script.id),
                "episode_id": str(script.episode_id),
                "version": script.version,
            },
        )

    def ensure_version_available(self, episode_id: EpisodeId, version: int) -> None:
        """Raise if the requested version already exists."""
        if Script.objects.filter(episode_id=episode_id, version=version).exists():
            raise ScriptVersionConflictError(
                f"Script version {version} already exists for episode {episode_id}."
            )
