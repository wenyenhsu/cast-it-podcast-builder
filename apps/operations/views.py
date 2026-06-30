"""Standalone operations dashboard views."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from apps.episodes.models import Episode
from apps.operations.decorators import staff_required
from services.admin.health import AdminHealthService
from services.admin.log_query import LogQueryService
from services.admin.metrics import MetricsService
from services.admin.pipeline import EpisodePipelineService
from services.admin.provider_status import ProviderDashboardService
from services.admin.stats import DashboardStatsService


def _operations_links() -> list[dict[str, str]]:
    return [
        {
            "label": "Provider Dashboard",
            "url": reverse("operations:providers"),
            "icon": "bi-hdd-network",
        },
        {
            "label": "Health Dashboard",
            "url": reverse("operations:health"),
            "icon": "bi-heart-pulse",
        },
        {
            "label": "Metrics Dashboard",
            "url": reverse("operations:metrics"),
            "icon": "bi-graph-up",
        },
        {
            "label": "Logs Viewer",
            "url": reverse("operations:logs"),
            "icon": "bi-journal-text",
        },
    ]


@staff_required
def dashboard(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "operations/dashboard.html",
        {
            **DashboardStatsService().overview(),
            "operations_links": _operations_links(),
        },
    )


@staff_required
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
        "operations/providers.html",
        {"providers": providers, "title": "Provider Dashboard", "message": message},
    )


@staff_required
def health_dashboard(request: HttpRequest) -> HttpResponse:
    components = AdminHealthService().full_report()
    return render(
        request,
        "operations/health.html",
        {"components": components, "title": "Health Dashboard"},
    )


@staff_required
def metrics_dashboard(request: HttpRequest) -> HttpResponse:
    days = int(request.GET.get("days", "7"))
    metrics = MetricsService().summary(days=days)
    return render(
        request,
        "operations/metrics.html",
        {"metrics": metrics, "title": "Metrics Dashboard", "days": days},
    )


@staff_required
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
        "operations/logs.html",
        {
            "entries": entries,
            "title": "Logs Viewer",
            "filters": request.GET,
        },
    )


@staff_required
def episode_pipeline(request: HttpRequest, episode_id: str) -> HttpResponse:
    episode = get_object_or_404(Episode, pk=episode_id)
    stages = EpisodePipelineService().as_dicts(episode)
    return render(
        request,
        "operations/episode_pipeline.html",
        {
            "episode": episode,
            "stages": stages,
            "title": f"Pipeline — {episode.title}",
        },
    )
