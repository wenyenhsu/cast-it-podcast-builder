"""Standalone operations dashboard views."""

import logging

from django.contrib import messages
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from apps.articles.models import Article
from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode
from apps.scheduler.models import Job, JobStatus
from apps.operations.decorators import staff_required
from apps.providers.models import ProviderType
from apps.scripts.models import Script, ScriptStatus
from services.admin.content_library import ContentLibraryError, ContentLibraryService
from services.admin.health import AdminHealthService
from services.admin.log_query import LogQueryService
from services.admin.metrics import MetricsService
from services.admin.news_sources import NewsSourceDashboardService, NewsSourceFormError
from services.admin.pipeline import EpisodePipelineService
from services.admin.provider_status import ProviderDashboardService
from services.admin.dispatch import AdminJobDispatchService
from services.admin.job_progress import JobProgressService
from services.admin.manual_script import ManualScriptError, ManualScriptService
from services.admin.scripts_dashboard import ScriptDashboardService
from services.admin.stats import DashboardStatsService
from services.audio.utils.paths import resolve_media_path

logger = logging.getLogger(__name__)

_MONITOR_TABS = frozenset({"health", "metrics", "logs"})
_PROVIDER_TABS = frozenset({"llm", "tts", "sources"})
_RESOURCE_TABS = frozenset({"rss", "manual"})
_CONTENT_FILTER_TABS = frozenset({"all", "rss", "manual"})
_CONTENT_VIEWS = frozenset(
    {
        "articles",
        "scripts",
        "failed-jobs",
        "episodes-today",
        "fail-log",
    }
)


def _content_filter(request: HttpRequest) -> str:
    value = request.GET.get("type") or request.POST.get("type", "all")
    if value not in _CONTENT_FILTER_TABS:
        return "all"
    return value


def _content_view(request: HttpRequest) -> str:
    value = request.GET.get("view", "articles")
    if value not in _CONTENT_VIEWS:
        return "articles"
    return value


def _content_redirect(
    content_filter: str = "all",
    *,
    job_id: str = "",
    aborted_job_id: str = "",
    content_view: str = "",
    episode_id: str = "",
) -> str:
    if content_filter == "all":
        base = reverse("operations:content")
    else:
        base = f"{reverse('operations:content')}?type={content_filter}"
    params: list[str] = []
    if content_view and content_view != "articles":
        params.append(f"view={content_view}")
    if episode_id:
        params.append(f"episode={episode_id}")
    if job_id:
        params.append(f"job={job_id}")
    if aborted_job_id:
        params.append(f"aborted_job={aborted_job_id}")
    if not params:
        return base
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{'&'.join(params)}"


def _scripts_tab_url(*, episode_id: str = "") -> str:
    return _content_redirect(content_view="scripts", episode_id=episode_id)


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
    content_view = _content_view(request)
    provider_type = None
    if content_filter == "rss":
        provider_type = ProviderType.RSS
    elif content_filter == "manual":
        provider_type = ProviderType.MANUAL

    stats = DashboardStatsService()
    overview = stats.overview()
    context: dict[str, object] = {
        "content_filter": content_filter,
        "content_view": content_view,
        "pipeline_stats": {
            "failed_jobs": overview["failed_jobs"],
            "episodes_today": overview["episodes_generated_today"],
            "scripts_total": overview["scripts_total"],
        },
        "articles": service.list_articles(provider_type=provider_type),
        "article_totals": service.article_totals(),
        "script_workspace": service.script_workspace(),
    }

    if content_view == "failed-jobs":
        context["failed_jobs"] = stats.list_failed_jobs()
    elif content_view == "episodes-today":
        context["episodes_today"] = stats.list_episodes_today()
    elif content_view == "fail-log":
        log_service = LogQueryService()
        context["fail_log_entries"] = log_service.search(
            search=request.GET.get("q", ""),
            severity=request.GET.get("severity", ""),
            job_id=request.GET.get("job_id", ""),
            episode_id=request.GET.get("episode_id", ""),
            provider=request.GET.get("provider", ""),
            limit=100,
        )
        context["fail_log_filters"] = request.GET
    elif content_view == "scripts":
        context.update(_scripts_tab_context(request))

    return context


def _scripts_tab_context(request: HttpRequest) -> dict[str, object]:
    episode_id = request.GET.get("episode", "") or request.POST.get("episode_id", "")
    episode = Episode.objects.filter(pk=episode_id).first() if episode_id else None
    manual_service = ManualScriptService()
    form_defaults = manual_service.form_defaults()
    if request.method == "POST" and request.POST.get("script_action"):
        form_defaults = manual_service.form_defaults(dict(request.POST.items()))
    elif episode is not None and not form_defaults.get("title"):
        form_defaults = {**form_defaults, "title": episode.title}
    return {
        "scripts_episode_id": episode_id,
        "scripts_episode": episode,
        "scripts": ScriptDashboardService().list_scripts(episode_id=episode_id),
        "manual_form_defaults": form_defaults,
    }


def _handle_content_post(request: HttpRequest) -> dict[str, str]:
    action = request.POST.get("content_action", "")
    content_filter = _content_filter(request)
    service = ContentLibraryService()

    try:
        if action == "save_script_sources":
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

        if action == "generate_script":
            episode_id, job_id = service.queue_script_generation(
                episode_title=request.POST.get("episode_title", ""),
            )
            return {
                "message": (
                    f'Script generation queued for "{request.POST.get("episode_title", "").strip()}" '
                    f"(job {job_id})."
                ),
                "type": content_filter,
                "job_id": job_id,
            }

        if action == "abort_script":
            aborted_job_id = service.abort_script_generation()
            return {
                "message": f"Script generation aborted (job {aborted_job_id}).",
                "type": content_filter,
                "aborted_job_id": aborted_job_id,
            }

        if action == "delete_episode":
            episode_id = request.POST.get("episode_id", "")
            title = service.delete_episode(episode_id)
            return {
                "message": f'Episode "{title}" deleted.',
                "type": content_filter,
                "content_view": request.POST.get("content_view", "episodes-today"),
            }
    except ContentLibraryError as exc:
        return {"error": exc.message, "type": content_filter}
    except Exception:
        return {
            "error": "Could not complete that action. Check LLM health and try again.",
            "type": content_filter,
        }

    return {"error": "Unknown action.", "type": content_filter}


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
        if request.POST.get("script_action"):
            result = _handle_scripts_post(request)
            if result.get("error"):
                context = {
                    "title": "Content",
                    **_content_context(request),
                    "content_view": "scripts",
                    **_scripts_tab_context(request),
                    "error": result["error"],
                }
                return render(request, "operations/content.html", context)
            messages.success(request, result.get("message", "Saved."))
            script_id = result.get("script_id")
            if script_id:
                return redirect(reverse("operations:script_detail", args=[script_id]))
            redirect_episode_id = result.get("episode_id") or request.POST.get(
                "episode_id", ""
            )
            return redirect(_scripts_tab_url(episode_id=redirect_episode_id))

        result = _handle_content_post(request)
        if result.get("error"):
            context = {
                "title": "Content",
                **_content_context(request),
                "error": result["error"],
            }
            return render(request, "operations/content.html", context)
        messages.success(request, result.get("message", "Saved."))
        return redirect(
            _content_redirect(
                str(result.get("type", "all")),
                job_id=str(result.get("job_id", "")),
                aborted_job_id=str(result.get("aborted_job_id", "")),
                content_view=str(result.get("content_view", "")),
            )
        )

    return render(
        request,
        "operations/content.html",
        {
            "title": "Content",
            **_content_context(request),
        },
    )


def _scripts_list_url(*, episode_id: str = "") -> str:
    return _scripts_tab_url(episode_id=episode_id)


def _handle_scripts_post(request: HttpRequest) -> dict[str, str]:
    action = request.POST.get("script_action", "")
    episode_id = request.GET.get("episode", "") or request.POST.get("episode_id", "")

    if action == "delete_script":
        script_id = request.POST.get("script_id", "").strip()
        if not script_id:
            return {"error": "Script not found."}
        try:
            deleted = ScriptDashboardService().delete_script(script_id)
        except ValueError as exc:
            return {"error": str(exc)}
        return {
            "message": (
                f'Deleted script v{deleted["version"]} for '
                f'"{deleted["episode_title"]}".'
            ),
            "episode_id": deleted["episode_id"],
        }

    if action != "create_manual_script":
        return {"error": "Unknown action."}

    try:
        script = ManualScriptService().create(
            title=request.POST.get("script_title", ""),
            dialogue=request.POST.get("script_dialogue", ""),
            episode_id=episode_id or None,
        )
        return {
            "message": (
                f'Manual script saved for "{script.episode.title}" (v{script.version}). '
                "Open it to generate TTS audio."
            ),
            "script_id": str(script.id),
        }
    except ManualScriptError as exc:
        return {"error": exc.message}
    except Exception:
        return {"error": "Could not save manual script. Check your input and try again."}


@staff_required
def scripts(request: HttpRequest) -> HttpResponse:
    episode_id = request.GET.get("episode", "") or request.POST.get("episode_id", "")
    if request.method == "POST":
        result = _handle_scripts_post(request)
        if result.get("error"):
            messages.error(request, result["error"])
            return redirect(_scripts_tab_url(episode_id=episode_id))
        messages.success(request, result.get("message", "Saved."))
        script_id = result.get("script_id")
        if script_id:
            return redirect(reverse("operations:script_detail", args=[script_id]))
        return redirect(
            _scripts_tab_url(episode_id=result.get("episode_id") or episode_id)
        )
    return redirect(_scripts_tab_url(episode_id=episode_id))


@staff_required
def script_detail(request: HttpRequest, script_id: str) -> HttpResponse:
    service = ScriptDashboardService()
    script = service.get_script_detail(script_id)
    if script is None:
        get_object_or_404(Script, pk=script_id)

    if request.method == "POST":
        action = request.POST.get("script_action", "")
        if action == "generate_audio":
            if script["status"] not in {"ready", "approved"}:
                messages.error(
                    request,
                    "Script must be ready before generating TTS audio.",
                )
            else:
                try:
                    job = AdminJobDispatchService().generate_audio(
                        script["episode_id"],
                        script_id=str(script_id),
                    )
                    messages.success(
                        request,
                        f"TTS audio generation queued (job {job.id}).",
                    )
                    return redirect(
                        f"{reverse('operations:script_detail', args=[script_id])}?job={job.id}"
                    )
                except Exception as exc:
                    logger.exception(
                        "Failed to queue TTS audio generation",
                        extra={
                            "event": "generate_audio_queue_failed",
                            "script_id": str(script_id),
                        },
                    )
                    messages.error(
                        request,
                        f"Could not queue audio generation: {exc}",
                    )
        else:
            messages.error(request, "Unknown action.")
        return redirect(reverse("operations:script_detail", args=[script_id]))

    return render(
        request,
        "operations/script_detail.html",
        {
            "script": script,
            "title": script["title"],
            "back_url": _scripts_list_url(episode_id=script["episode_id"]),
            "content_url": reverse("operations:content"),
            "pipeline_url": reverse(
                "operations:episode_pipeline",
                args=[script["episode_id"]],
            ),
            "can_generate_audio": script["status"] in {"ready", "approved"},
        },
    )


@staff_required
def tts_generation(request: HttpRequest) -> HttpResponse:
    """Open the TTS studio for a ready script (by script or episode)."""
    script_id = request.GET.get("script", "").strip()
    if script_id:
        script = Script.objects.filter(pk=script_id).first()
        if script is None:
            messages.error(request, "Script not found.")
            return redirect(f"{reverse('operations:content')}?view=scripts")
        return redirect(reverse("operations:script_detail", args=[script.pk]))

    episode_id = request.GET.get("episode", "").strip()
    if episode_id:
        script = (
            Script.objects.filter(
                episode_id=episode_id,
                status__in=[ScriptStatus.READY, ScriptStatus.APPROVED],
            )
            .order_by("-version")
            .first()
        )
        if script is not None:
            return redirect(reverse("operations:script_detail", args=[script.pk]))
        messages.error(
            request,
            "No ready script for this episode yet. Generate or add a manual script first.",
        )
        return redirect(f"{reverse('operations:content')}?view=episodes-today")

    workspace = ContentLibraryService().script_workspace()
    script_id = workspace.get("latest_ready_script_id", "")
    if script_id:
        return redirect(reverse("operations:script_detail", args=[script_id]))
    messages.error(
        request,
        "No ready script for TTS yet. Generate or add a manual script first.",
    )
    return redirect(reverse("operations:content"))


@staff_required
def audio_asset(request: HttpRequest, asset_id: str) -> FileResponse:
    """Stream a generated segment audio file for in-browser playback."""
    asset = get_object_or_404(
        AudioAsset.objects.filter(status=AudioAssetStatus.READY),
        pk=asset_id,
    )
    path = resolve_media_path(asset.file_path)
    if not path.is_file():
        raise Http404("Audio file not found on disk.")

    content_type = f"audio/{asset.format}" if asset.format else "audio/wav"
    return FileResponse(path.open("rb"), content_type=content_type)


@staff_required
def job_status_api(request: HttpRequest, job_id: str) -> JsonResponse:
    """JSON job status for operations progress polling."""
    del request
    job = get_object_or_404(Job, pk=job_id)
    return JsonResponse(JobProgressService().serialize_job(job))


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
def dashboard_insights(request: HttpRequest) -> HttpResponse:
    tab = request.GET.get("tab", "failed-jobs")
    view_map = {
        "failed-jobs": "failed-jobs",
        "episodes-today": "episodes-today",
    }
    view = view_map.get(tab, "failed-jobs")
    return redirect(f"{reverse('operations:content')}?view={view}")


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
    panel = EpisodePipelineService().build_panel(episode)
    stages = panel["stages"]
    script_stage = next((stage for stage in stages if stage["name"] == "Script"), None)
    pipeline_notice = ""
    if script_stage and script_stage["status"] in {"queued", JobStatus.QUEUED}:
        pipeline_notice = (
            "Script job is queued. If it stays here, ensure celery-worker is running "
            "and listening to the llm queue, then retry from Content → Generate Script."
        )
    return render(
        request,
        "operations/episode_pipeline.html",
        {
            "episode": episode,
            "stages": stages,
            "overview": panel["overview"],
            "title": f"Pipeline — {episode.title}",
            "pipeline_notice": pipeline_notice,
        },
    )
