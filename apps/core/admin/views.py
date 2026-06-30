"""Custom admin views for operations dashboards."""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.admin import AdminSite
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import URLPattern, path

from apps.episodes.models import Episode
from services.admin.health import AdminHealthService
from services.admin.log_query import LogQueryService
from services.admin.metrics import MetricsService
from services.admin.pipeline import EpisodePipelineService
from services.admin.provider_status import ProviderDashboardService


@staff_member_required
def provider_dashboard(request: HttpRequest) -> HttpResponse:
    service = ProviderDashboardService()
    if request.method == "POST":
        providers = service.run_health_checks()
        message = "Provider health checks completed."
    else:
        providers = service.snapshot()
        message = ""
    return render(
        request,
        "admin/operations/provider_dashboard.html",
        {"providers": providers, "title": "Provider Dashboard", "message": message},
    )


@staff_member_required
def health_dashboard(request: HttpRequest) -> HttpResponse:
    components = AdminHealthService().full_report()
    return render(
        request,
        "admin/operations/health_dashboard.html",
        {"components": components, "title": "Health Dashboard"},
    )


@staff_member_required
def metrics_dashboard(request: HttpRequest) -> HttpResponse:
    days = int(request.GET.get("days", "7"))
    metrics = MetricsService().summary(days=days)
    return render(
        request,
        "admin/operations/metrics_dashboard.html",
        {"metrics": metrics, "title": "Metrics Dashboard", "days": days},
    )


@staff_member_required
def logs_viewer(request: HttpRequest) -> HttpResponse:
    service = LogQueryService()
    entries = service.search(
        search=request.GET.get("q", ""),
        severity=request.GET.get("severity", ""),
        job_id=request.GET.get("job_id", ""),
        episode_id=request.GET.get("episode_id", ""),
        provider=request.GET.get("provider", ""),
        limit=100,
    )
    return render(
        request,
        "admin/operations/logs_viewer.html",
        {
            "entries": entries,
            "title": "Logs Viewer",
            "filters": request.GET,
        },
    )


@staff_member_required
def episode_pipeline(request: HttpRequest, episode_id: str) -> HttpResponse:
    episode = get_object_or_404(Episode, pk=episode_id)
    stages = EpisodePipelineService().as_dicts(episode)
    return render(
        request,
        "admin/operations/episode_pipeline.html",
        {"episode": episode, "stages": stages, "title": f"Pipeline — {episode.title}"},
    )


def get_operations_urls(admin_site: AdminSite) -> list[URLPattern]:
    """Return custom admin URL patterns."""
    return [
        path(
            "operations/providers/",
            admin_site.admin_view(provider_dashboard),
            name="operations_providers",
        ),
        path(
            "operations/health/",
            admin_site.admin_view(health_dashboard),
            name="operations_health",
        ),
        path(
            "operations/metrics/",
            admin_site.admin_view(metrics_dashboard),
            name="operations_metrics",
        ),
        path(
            "operations/logs/",
            admin_site.admin_view(logs_viewer),
            name="operations_logs",
        ),
        path(
            "operations/pipeline/<uuid:episode_id>/",
            admin_site.admin_view(episode_pipeline),
            name="operations_episode_pipeline",
        ),
    ]
