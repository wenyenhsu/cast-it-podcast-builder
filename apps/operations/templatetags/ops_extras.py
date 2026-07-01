"""Template helpers for the operations UI."""

from django import template
from django.template.defaultfilters import date as format_date
from django.utils import timezone

register = template.Library()


@register.filter
def local_datetime(value: object) -> str:
    """Format an aware datetime in the configured Django timezone."""
    if not value:
        return "—"
    localized = timezone.localtime(value)
    return format_date(localized, "M j, g:i A")


@register.filter
def local_datetime_title(value: object) -> str:
    """Tooltip-friendly local datetime with timezone name."""
    if not value:
        return ""
    localized = timezone.localtime(value)
    return format_date(localized, "Y-m-d H:i:s T")
