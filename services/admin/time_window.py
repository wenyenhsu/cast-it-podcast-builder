"""Local-time helpers for operations dashboards."""

from django.utils import timezone


def local_start_of_day():
    """Return midnight at the start of the current local calendar day."""
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)
