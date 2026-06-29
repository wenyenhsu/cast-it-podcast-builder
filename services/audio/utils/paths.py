"""Path resolution helpers for audio files."""

from pathlib import Path

from django.conf import settings


def resolve_media_path(file_path: str, *, media_root: Path | None = None) -> Path:
    """Resolve a stored file path against MEDIA_ROOT."""
    path = Path(file_path)
    if path.is_absolute():
        return path
    root = media_root or Path(getattr(settings, "MEDIA_ROOT", Path("media")))
    return root / path


def build_concat_list_content(paths: list[Path]) -> str:
    """Build FFmpeg concat demuxer list file content."""
    lines = [f"file '{path.resolve()}'" for path in paths]
    return "\n".join(lines) + "\n"
