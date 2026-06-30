"""Standalone operations dashboard views."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.episodes.models import Episode
from apps.operations.decorators import staff_required
from services.admin.health import AdminHealthService
from services.admin.log_query import LogQueryService
from services.admin.metrics import MetricsService
from services.admin.pipeline import EpisodePipelineService
from services.admin.provider_status import ProviderDashboardService
from services.admin.stats import DashboardStatsService

_MONITOR_TABS = frozenset({"health", "metrics", "logs"})
_PROVIDER_TABS = frozenset({"llm", "tts"})


def _operations_links() -> list[dict[str, str]]:
    return [
        {
            "label": "Providers",
            "url": reverse("operations:providers"),
            "icon": "bi-hdd-network",
        },
        {
            "label": "Monitor",
            "url": reverse("operations:monitor"),
            "icon": "bi-activity",
        },
    ]


def _monitor_context(request: HttpRequest) -> dict[str, object]:
    tab = request.GET.get("tab", "health")
    if tab not in _MONITOR_TABS:
        tab = "health"

    days = int(request.GET.get("days", "7"))
    log_service = LogQueryService()

    return {
        "title": "Monitor",
        "tab": tab,
        "days": days,
        "components": AdminHealthService().full_report(),
        "metrics": MetricsService().summary(days=days),
        "entries": log_service.search(
            search=request.GET.get("q", ""),
            severity=request.GET.get("severity", ""),
            job_id=request.GET.get("job_id", ""),
            episode_id=request.GET.get("episode_id", ""),
            provider=request.GET.get("provider", ""),
            limit=100,
        ),
        "filters": request.GET,
    }


def _providers_context(request: HttpRequest) -> dict[str, object]:
    tab = request.GET.get("tab") or request.POST.get("tab", "llm")
    if tab not in _PROVIDER_TABS:
        tab = "llm"

    service = ProviderDashboardService()
    message = ""
    if request.method == "POST":
        if tab == "tts":
            message = "TTS health check completed."
        else:
            message = "LLM health check completed."

    return {
        "title": "Providers",
        "tab": tab,
        "message": message,
        "llm": service.llm_status(),
        "tts": service.tts_status(),
    }


@staff_required
def dashboard(request: HttpRequest) -> HttpResponse:
    service = ProviderDashboardService()
    return render(
        request,
        "operations/dashboard.html",
        {
            **DashboardStatsService().overview(),
            "operations_links": _operations_links(),
            "provider_snapshots": service.snapshot(),
        },
    )


@staff_required
def providers(request: HttpRequest) -> HttpResponse:
    return render(request, "operations/providers.html", _providers_context(request))


@staff_required
def llm_provider_dashboard(request: HttpRequest) -> HttpResponse:
    return redirect(f"{reverse('operations:providers')}?tab=llm")


@staff_required
def tts_provider_dashboard(request: HttpRequest) -> HttpResponse:
    return redirect(f"{reverse('operations:providers')}?tab=tts")


@staff_required
def monitor(request: HttpRequest) -> HttpResponse:
    return render(request, "operations/monitor.html", _monitor_context(request))


@staff_required
def health_dashboard(request: HttpRequest) -> HttpResponse:
    return redirect(f"{reverse('operations:monitor')}?tab=health")


@staff_required
def metrics_dashboard(request: HttpRequest) -> HttpResponse:
    days = request.GET.get("days", "7")
    return redirect(f"{reverse('operations:monitor')}?tab=metrics&days={days}")


@staff_required
def logs_viewer(request: HttpRequest) -> HttpResponse:
    query = request.GET.urlencode()
    base = f"{reverse('operations:monitor')}?tab=logs"
    if query:
        return redirect(f"{base}&{query}")
    return redirect(base)


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
