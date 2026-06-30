"""Colored status badges for Django Admin list displays."""

from django.utils.html import format_html

STATUS_COLORS: dict[str, str] = {
    "pending": "#6c757d",
    "queued": "#0dcaf0",
    "running": "#0d6efd",
    "in_progress": "#0d6efd",
    "generating": "#0d6efd",
    "retrying": "#fd7e14",
    "failed": "#dc3545",
    "cancelled": "#6610f2",
    "completed": "#198754",
    "succeeded": "#198754",
    "ready": "#198754",
    "healthy": "#198754",
    "unhealthy": "#dc3545",
    "unknown": "#6c757d",
    "draft": "#6c757d",
    "collecting": "#0dcaf0",
    "generating_script": "#0d6efd",
    "generating_audio": "#0d6efd",
    "publishing": "#fd7e14",
    "processed": "#20c997",
    "selected": "#0d6efd",
    "used": "#198754",
    "archived": "#adb5bd",
}


def status_badge(status: str) -> str:
    """Render a colored HTML badge for a status value."""
    normalized = (status or "unknown").lower()
    color = STATUS_COLORS.get(normalized, "#495057")
    label = status.replace("_", " ").title() if status else "Unknown"
    return format_html(
        '<span class="ops-status-badge" style="background-color: {}; color: #fff;'
        ' padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;">'
        "{}</span>",
        color,
        label,
    )


def health_badge(status: str) -> str:
    """Render a health status badge."""
    color_map = {
        "Healthy": "#198754",
        "Warning": "#fd7e14",
        "Error": "#dc3545",
    }
    color = color_map.get(status, "#6c757d")
    return format_html(
        '<span class="ops-health-badge" style="background-color: {}; color: #fff;'
        ' padding: 3px 10px; border-radius: 999px; font-size: 11px; font-weight: 600;">'
        "{}</span>",
        color,
        status,
    )
