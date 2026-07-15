"""Extended health checks for the admin health dashboard."""

import shutil
from typing import Any

from django.conf import settings as django_settings
from django.core.cache import cache

from api.v1.services.health import ApiHealthService
from services.audio.pipeline.settings import AudioSettings


class AdminHealthService:
    """Infrastructure health summary for the operations console."""

    def full_report(self) -> list[dict[str, Any]]:
        api_health = ApiHealthService().overall()
        return [
            self._postgres(),
            self._redis(),
            self._celery(api_health.get("checks", {}).get("celery", {})),
            self._ollama(api_health.get("checks", {}).get("llm", {})),
            self._chatterbox(api_health.get("checks", {}).get("tts", {})),
            self._supabase(),
            self._ffmpeg(),
            self._storage(),
        ]

    def _postgres(self) -> dict[str, Any]:
        try:
            from django.db import connection

            connection.ensure_connection()
            healthy = True
            detail = "Connected"
            status = "Healthy"
        except Exception as exc:
            healthy = False
            detail = str(exc)
            status = "Error"
        return {
            "name": "PostgreSQL",
            "status": status,
            "healthy": healthy,
            "detail": detail,
        }

    def _redis(self) -> dict[str, Any]:
        try:
            cache.set("admin_health_ping", "ok", timeout=5)
            healthy = cache.get("admin_health_ping") == "ok"
            status = "Healthy" if healthy else "Error"
            detail = "Cache reachable" if healthy else "Cache unreachable"
        except Exception as exc:
            healthy = False
            status = "Error"
            detail = str(exc)
        return {"name": "Redis", "status": status, "healthy": healthy, "detail": detail}

    def _celery(self, data: dict[str, Any]) -> dict[str, Any]:
        healthy = bool(data.get("healthy"))
        status = "Healthy" if healthy else "Warning"
        return {
            "name": "Celery",
            "status": status,
            "healthy": healthy,
            "detail": f"Workers: {data.get('workers', False)}",
        }

    def _ollama(self, data: dict[str, Any]) -> dict[str, Any]:
        healthy = bool(data.get("healthy"))
        status = "Healthy" if healthy else "Error"
        return {
            "name": "Ollama",
            "status": status,
            "healthy": healthy,
            "detail": f"Provider: {data.get('provider', 'unknown')}",
        }

    def _chatterbox(self, data: dict[str, Any]) -> dict[str, Any]:
        healthy = bool(data.get("healthy"))
        status = "Healthy" if healthy else "Error"
        return {
            "name": "Chatterbox",
            "status": status,
            "healthy": healthy,
            "detail": f"Provider: {data.get('provider', 'unknown')}",
        }

    def _supabase(self) -> dict[str, Any]:
        from services.publish.supabase_publisher import SupabasePublisher

        probe = SupabasePublisher(require_config=False).probe_health()
        if not probe.configured:
            status = "Warning"
        elif probe.healthy:
            status = "Healthy"
        else:
            status = "Error"
        return {
            "name": "Supabase",
            "status": status,
            "healthy": probe.healthy,
            "detail": probe.detail,
        }

    def _ffmpeg(self) -> dict[str, Any]:
        audio_settings = AudioSettings.from_django_settings()
        ffmpeg = shutil.which(audio_settings.ffmpeg_binary)
        ffprobe = shutil.which(audio_settings.ffprobe_binary)
        healthy = bool(ffmpeg and ffprobe)
        status = "Healthy" if healthy else "Error"
        detail = f"ffmpeg={ffmpeg or 'missing'}, ffprobe={ffprobe or 'missing'}"
        return {
            "name": "FFmpeg",
            "status": status,
            "healthy": healthy,
            "detail": detail,
        }

    def _storage(self) -> dict[str, Any]:
        media_root = django_settings.MEDIA_ROOT
        try:
            media_root.mkdir(parents=True, exist_ok=True)
            test_file = media_root / ".admin_health_check"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            healthy = True
            status = "Healthy"
            detail = str(media_root)
        except Exception as exc:
            healthy = False
            status = "Error"
            detail = str(exc)
        return {
            "name": "Storage",
            "status": status,
            "healthy": healthy,
            "detail": detail,
        }
