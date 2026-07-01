"""Episode naming helpers — single source of truth is Episode.title."""

import re

from apps.episodes.models import Episode
from apps.scripts.models import Script

_DRAFT_TITLE_PATTERN = re.compile(r"^Draft \d{4}-\d{2}-\d{2}$")


def normalize_episode_name(name: str) -> str:
    """Normalize user-facing episode names from form input."""
    cleaned = name.strip()
    if cleaned.lower().startswith("episode:"):
        cleaned = cleaned.split(":", 1)[1].strip()
    return cleaned


def is_placeholder_episode_title(title: str) -> bool:
    """Return True for auto-generated draft episode names."""
    return bool(_DRAFT_TITLE_PATTERN.match(title.strip()))


def apply_episode_name(episode: Episode, name: str) -> str:
    """Set episode.title from user or generated input."""
    cleaned = normalize_episode_name(name)
    if not cleaned:
        return episode.title
    if episode.title != cleaned:
        episode.title = cleaned
        episode.save(update_fields=["title", "updated_at"])
    return cleaned


def consolidate_legacy_script_titles() -> int:
    """Copy script.title into episode.title for legacy rows; clear script.title."""
    updated = 0
    for script in Script.objects.select_related("episode").exclude(title=""):
        episode = script.episode
        script_name = normalize_episode_name(script.title)
        if script_name and (
            is_placeholder_episode_title(episode.title)
            or not episode.title.strip()
        ):
            if episode.title != script_name:
                episode.title = script_name
                episode.save(update_fields=["title", "updated_at"])
                updated += 1
        if script.title:
            script.title = ""
            script.save(update_fields=["title", "updated_at"])
    return updated
