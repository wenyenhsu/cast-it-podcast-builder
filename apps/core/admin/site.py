"""Django Admin site customization."""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.template.response import TemplateResponse
from django.urls import URLPattern, URLResolver

from apps.core.admin.views import get_operations_urls
from services.admin.stats import DashboardStatsService


def patch_admin_site(site: admin.AdminSite) -> None:
    """Configure the default admin site for operations use."""
    site.site_header = "Cast It Operations Console"
    site.site_title = "Cast It Ops"
    site.index_title = "Operations Dashboard"

    original_get_urls = site.get_urls

    def get_urls() -> list[URLPattern | URLResolver]:
        return get_operations_urls(site) + original_get_urls()

    site.get_urls = get_urls  # type: ignore[method-assign]

    original_index = site.index

    def index(
        request: HttpRequest,
        extra_context: dict[str, Any] | None = None,
    ) -> TemplateResponse:
        context = {
            **DashboardStatsService().overview(),
            "operations_links": _operations_links(),
        }
        if extra_context:
            context.update(extra_context)
        return original_index(request, extra_context=context)

    site.index = index  # type: ignore[method-assign]


def _operations_links() -> list[dict[str, str]]:
    return [
        {"label": "Provider Dashboard", "url": "operations/providers/"},
        {"label": "Health Dashboard", "url": "operations/health/"},
        {"label": "Metrics Dashboard", "url": "operations/metrics/"},
        {"label": "Logs Viewer", "url": "operations/logs/"},
    ]
