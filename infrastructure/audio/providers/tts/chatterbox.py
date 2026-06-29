"""Chatterbox TTS Server provider adapter."""

import logging
import tempfile
import time
from pathlib import Path
from typing import Any, Protocol

from domain.audio.config import TTSProviderConfig
from domain.audio.dtos import TTSRequest, TTSResponse, VoiceInfo
from domain.audio.exceptions import (
    ProviderUnavailableException,
    TTSException,
    VoiceNotFoundException,
)
from infrastructure.audio.providers.tts.base import BaseTTSProvider
from services.audio.wav_utils import parse_wav_duration_seconds

logger = logging.getLogger(__name__)

DEFAULT_LANGUAGES = ["en"]
SUPPORTED_FORMATS = ["wav", "mp3", "opus"]


class HTTPClientProtocol(Protocol):
    """Protocol for HTTP clients used by ChatterboxProvider."""

    def get(self, url: str, *, timeout: float) -> Any: ...

    def post(
        self,
        url: str,
        *,
        json: dict[str, Any],
        timeout: float,
    ) -> Any: ...


class ChatterboxProvider(BaseTTSProvider):
    """Adapter for the Chatterbox TTS Server HTTP API."""

    def __init__(
        self,
        config: TTSProviderConfig,
        http_client: HTTPClientProtocol | None = None,
        temp_dir: Path | None = None,
    ) -> None:
        self._config = config
        self._base_url = config.base_url.rstrip("/")
        self._timeout = config.timeout
        self._default_voice = config.default_voice
        self._temp_dir = temp_dir

        if http_client is None:
            import httpx

            http_client = httpx.Client()
        self._http = http_client
        self._cached_languages: list[str] | None = None

    @property
    def provider_name(self) -> str:
        return "chatterbox"

    def generate_segment(self, request: TTSRequest) -> TTSResponse:
        voice_id = request.voice or self._default_voice
        if not voice_id:
            raise VoiceNotFoundException(
                "No voice specified for Chatterbox TTS request."
            )

        payload: dict[str, Any] = {
            "text": request.text,
            "voice_mode": "predefined",
            "predefined_voice_id": voice_id,
            "output_format": request.output_format or self._config.audio_format,
            "speed_factor": request.speed,
        }
        if request.language:
            payload["language"] = request.language

        started = time.perf_counter()
        try:
            response = self._http.post(
                f"{self._base_url}/tts",
                json=payload,
                timeout=self._timeout,
            )
        except Exception as exc:
            raise ProviderUnavailableException(
                f"Chatterbox TTS request failed: {exc}"
            ) from exc

        if response.status_code == 404:
            raise VoiceNotFoundException(f"Chatterbox voice not found: {voice_id}")
        if response.status_code >= 400:
            raise TTSException(
                f"Chatterbox TTS error {response.status_code}: {response.text}"
            )

        audio_bytes = response.content
        sample_rate, duration = parse_wav_duration_seconds(audio_bytes)
        output_format = request.output_format or self._config.audio_format
        audio_path = self._write_temp_file(audio_bytes, output_format)
        generation_time = time.perf_counter() - started

        logger.info(
            "Chatterbox segment generated",
            extra={
                "event": "chatterbox_segment_generated",
                "voice": voice_id,
                "duration": duration,
                "generation_time": generation_time,
            },
        )

        return TTSResponse(
            provider=self.provider_name,
            voice=voice_id,
            audio_file=audio_path,
            duration=duration,
            sample_rate=sample_rate,
            format=output_format,
            generation_time=generation_time,
        )

    def list_voices(self) -> list[VoiceInfo]:
        try:
            response = self._http.get(
                f"{self._base_url}/get_predefined_voices",
                timeout=self._timeout,
            )
            response.raise_for_status()
        except Exception as exc:
            raise ProviderUnavailableException(
                f"Failed to list Chatterbox voices: {exc}"
            ) from exc

        payload = response.json()
        voices: list[VoiceInfo] = []
        for item in payload:
            if isinstance(item, dict):
                voice_id = str(item.get("filename", ""))
                name = str(item.get("display_name", voice_id))
            else:
                voice_id = str(item)
                name = voice_id
            if voice_id:
                voices.append(VoiceInfo(voice_id=voice_id, name=name))
        return voices

    def health_check(self) -> bool:
        try:
            response = self._http.get(
                f"{self._base_url}/api/model-info",
                timeout=min(self._timeout, 10.0),
            )
            if response.status_code == 200:
                return True
            response = self._http.get(
                f"{self._base_url}/api/ui/initial-data",
                timeout=min(self._timeout, 10.0),
            )
            return response.status_code == 200
        except Exception:
            logger.warning(
                "Chatterbox health check failed",
                extra={"event": "chatterbox_health_check_failed"},
            )
            return False

    def estimate_duration(self, text: str, *, speed: float = 1.0) -> float:
        word_count = len(text.split())
        if word_count == 0:
            return 0.0
        base_duration = (word_count / self._config.words_per_minute) * 60
        adjusted = base_duration / speed if speed > 0 else base_duration
        return max(0.1, adjusted)

    def supported_languages(self) -> list[str]:
        if self._cached_languages is not None:
            return self._cached_languages

        try:
            response = self._http.get(
                f"{self._base_url}/api/model-info",
                timeout=min(self._timeout, 10.0),
            )
            if response.status_code == 200:
                data = response.json()
                languages = data.get("supported_languages") or data.get(
                    "SUPPORTED_LANGUAGES"
                )
                if isinstance(languages, dict):
                    self._cached_languages = sorted(languages.keys())
                    return self._cached_languages
                if isinstance(languages, list):
                    self._cached_languages = [str(lang) for lang in languages]
                    return self._cached_languages
        except Exception:
            logger.debug("Could not fetch Chatterbox supported languages")

        self._cached_languages = list(DEFAULT_LANGUAGES)
        return self._cached_languages

    def supported_formats(self) -> list[str]:
        return list(SUPPORTED_FORMATS)

    def _write_temp_file(self, audio_bytes: bytes, output_format: str) -> Path:
        suffix = f".{output_format.lstrip('.')}"
        temp_dir = self._temp_dir
        with tempfile.NamedTemporaryFile(
            suffix=suffix,
            delete=False,
            dir=temp_dir,
        ) as temp_file:
            temp_file.write(audio_bytes)
            return Path(temp_file.name)
