"""Standalone operations dashboard views."""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.articles.models import Article
from apps.episodes.models import Episode
from apps.operations.decorators import staff_required
from apps.providers.models import ProviderType
from services.admin.content_library import ContentLibraryService
from services.admin.health import AdminHealthService
from services.admin.log_query import LogQueryService
from services.admin.metrics import MetricsService
from services.admin.news_sources import NewsSourceDashboardService, NewsSourceFormError
from services.admin.pipeline import EpisodePipelineService
from services.admin.provider_status import ProviderDashboardService
from services.admin.stats import DashboardStatsService

_MONITOR_TABS = frozenset({"health", "metrics", "logs"})
_PROVIDER_TABS = frozenset({"llm", "tts", "sources"})
_RESOURCE_TABS = frozenset({"rss", "manual"})
_CONTENT_FILTER_TABS = frozenset({"all", "rss", "manual"})


def _content_filter(request: HttpRequest) -> str:
    value = request.GET.get("type") or request.POST.get("type", "all")
    if value not in _CONTENT_FILTER_TABS:
        return "all"
    return value


def _content_redirect(content_filter: str = "all") -> str:
    if content_filter == "all":
        return reverse("operations:content")
    return f"{reverse('operations:content')}?type={content_filter}"


def _resource_tab(request: HttpRequest) -> str:
    resource = request.GET.get("resource") or request.POST.get("resource", "rss")
    if resource not in _RESOURCE_TABS:
        return "rss"
    return resource


def _sources_redirect(resource: str) -> str:
    return f"{reverse('operations:providers')}?tab=sources&resource={resource}"


def _operations_links() -> list[dict[str, str]]:
    return [
        {
            "label": "Content",
            "url": reverse("operations:content"),
            "icon": "bi-journal-text",
        },
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


def _manual_form_defaults(request: HttpRequest) -> dict[str, str]:
    if (
        request.method == "POST"
        and request.POST.get("provider_action") == "create_manual_article"
    ):
        return {
            "title": request.POST.get("article_title", ""),
            "author": request.POST.get("article_author", ""),
            "url": request.POST.get("article_url", ""),
            "summary": request.POST.get("article_summary", ""),
            "content": request.POST.get("article_content", ""),
        }
    return {
        "title": "",
        "author": "",
        "url": "",
        "summary": "",
        "content": "",
    }


def _sources_context(
    request: HttpRequest,
    *,
    message: str = "",
    error: str = "",
) -> dict[str, object]:
    service = NewsSourceDashboardService()
    resource = _resource_tab(request)
    edit_id = request.GET.get("edit", "")
    edit_form = (
        service.get_edit_form(edit_id) if edit_id and resource == "rss" else None
    )
    return {
        "resource": resource,
        "sources": service.list_sources(provider_type=ProviderType.RSS),
        "recent_articles": service.recent_articles(
            provider_type=ProviderType.RSS if resource == "rss" else ProviderType.MANUAL,
        ),
        "article_totals": service.article_totals(),
        "manual_provider": service.manual_provider_overview(),
        "edit_form": edit_form,
        "form_defaults": edit_form
        or {
            "name": "",
            "rss_url": "",
            "language": "en",
            "enabled": True,
            "max_articles_per_import": 3,
        },
        "manual_form_defaults": _manual_form_defaults(request),
        "message": message,
        "error": error,
    }


def _handle_sources_post(request: HttpRequest) -> dict[str, str]:
    action = request.POST.get("provider_action", "")
    service = NewsSourceDashboardService()
    user_id = request.user.id if request.user.is_authenticated else None
    max_articles = int(request.POST.get("max_articles_per_import", "3") or "3")
    default_resource = _resource_tab(request)

    try:
        if action == "create_source":
            service.create_rss_source(
                name=request.POST.get("name", ""),
                rss_url=request.POST.get("rss_url", ""),
                language=request.POST.get("language", "en"),
                enabled=request.POST.get("enabled") == "on",
                max_articles_per_import=max_articles,
            )
            return {"message": "RSS source created.", "resource": "rss"}

        if action == "update_source":
            source_id = request.POST.get("source_id", "")
            service.update_rss_source(
                source_id,
                name=request.POST.get("name", ""),
                rss_url=request.POST.get("rss_url", ""),
                language=request.POST.get("language", "en"),
                enabled=request.POST.get("enabled") == "on",
                max_articles_per_import=max_articles,
            )
            return {"message": "RSS source updated.", "resource": "rss"}

        if action == "delete_source":
            service.delete_source(request.POST.get("source_id", ""))
            return {"message": "RSS source deleted.", "resource": "rss"}

        if action == "import_source":
            job_id = service.import_source(
                request.POST.get("source_id", ""),
                user_id=user_id,
            )
            detail = f" Import job queued ({job_id})." if job_id else ""
            return {
                "message": f"Article import started.{detail}",
                "resource": "rss",
            }

        if action == "toggle_enabled":
            source_id = request.POST.get("source_id", "")
            enabled = request.POST.get("enabled") == "true"
            service.toggle_source_enabled(source_id, enabled=enabled)
            state = "enabled" if enabled else "disabled"
            return {"message": f"Source {state}.", "resource": _resource_tab(request)}

        if action == "create_manual_article":
            manual_source = service.get_or_create_manual_source()
            article = service.create_manual_article(
                source_id=str(manual_source.id),
                title=request.POST.get("article_title", ""),
                content=request.POST.get("article_content", ""),
                summary=request.POST.get("article_summary", ""),
                author=request.POST.get("article_author", ""),
                url=request.POST.get("article_url", ""),
            )
            return {"message": f'Article "{article.title}" added.', "resource": "manual"}

    except NewsSourceFormError as exc:
        return {"error": exc.message, "resource": default_resource}
    except Exception:
        return {
            "error": "Could not complete that action. Check the source and try again.",
            "resource": default_resource,
        }

    return {"error": "Unknown action.", "resource": default_resource}


def _content_context(request: HttpRequest) -> dict[str, object]:
    service = ContentLibraryService()
    content_filter = _content_filter(request)
    provider_type = None
    if content_filter == "rss":
        provider_type = ProviderType.RSS
    elif content_filter == "manual":
        provider_type = ProviderType.MANUAL
    return {
        "content_filter": content_filter,
        "articles": service.list_articles(provider_type=provider_type),
        "article_totals": service.article_totals(),
    }


def _handle_content_post(request: HttpRequest) -> dict[str, str]:
    action = request.POST.get("content_action", "")
    content_filter = _content_filter(request)
    service = ContentLibraryService()

    if action != "save_script_sources":
        return {"error": "Unknown action.", "type": content_filter}

    selected_ids = set(request.POST.getlist("script_source_ids"))
    scope_ids = set(request.POST.getlist("article_scope_ids"))
    updated = service.update_script_selection(
        selected_ids=selected_ids,
        scope_ids=scope_ids,
    )
    episode_id = service.sync_selected_articles_to_draft_episode()
    message = f"Saved script sources ({updated} updated)."
    if episode_id:
        message += f" Draft episode {episode_id} updated."
    return {"message": message, "type": content_filter}


def _providers_context(request: HttpRequest) -> dict[str, object]:
    tab = request.GET.get("tab") or request.POST.get("tab", "llm")
    if tab not in _PROVIDER_TABS:
        tab = "llm"

    message = ""
    error = ""
    if request.method == "POST":
        if tab == "sources":
            result = _handle_sources_post(request)
            if result.get("error"):
                error = result["error"]
                context = {
                    "title": "Providers",
                    "tab": tab,
                    "message": message,
                    "error": error,
                    **_sources_context(request),
                }
                return context
            messages.success(request, result.get("message", "Saved."))
            resource = result.get("resource", _resource_tab(request))
            return {"redirect": _sources_redirect(str(resource))}
        elif tab == "tts":
            ProviderDashboardService().tts_status()
            message = "TTS health check completed."
        else:
            ProviderDashboardService().llm_status()
            message = "LLM health check completed."

    context: dict[str, object] = {
        "title": "Providers",
        "tab": tab,
        "message": message,
        "error": error,
    }

    if tab == "sources":
        context.update(_sources_context(request, message=message, error=error))
    else:
        service = ProviderDashboardService()
        context["llm"] = service.llm_status()
        context["tts"] = service.tts_status()

    return context


@staff_required
def content(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        result = _handle_content_post(request)
        if result.get("error"):
            context = {
                "title": "Content",
                **_content_context(request),
                "error": result["error"],
            }
            return render(request, "operations/content.html", context)
        messages.success(request, result.get("message", "Saved."))
        return redirect(_content_redirect(str(result.get("type", "all"))))

    return render(
        request,
        "operations/content.html",
        {
            "title": "Content",
            **_content_context(request),
        },
    )


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
    context = _providers_context(request)
    redirect_url = context.pop("redirect", None)
    if redirect_url:
        return redirect(redirect_url)
    return render(request, "operations/providers.html", context)


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
def article_detail(request: HttpRequest, article_id: str) -> HttpResponse:
    article = get_object_or_404(
        Article.objects.select_related("source"),
        pk=article_id,
    )
    resource = (
        "manual"
        if article.source.provider_type == ProviderType.MANUAL
        else "rss"
    )
    return render(
        request,
        "operations/article_detail.html",
        {
            "article": article,
            "title": article.title,
            "back_url": reverse("operations:content"),
            "providers_url": _sources_redirect(resource),
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
