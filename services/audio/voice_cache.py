"""Voice and provider capability cache."""

import logging

from django.core.cache import cache

from domain.audio.constants import HEALTH_CACHE_TTL_SECONDS, VOICE_CACHE_TTL_SECONDS
from domain.audio.dtos import ProviderCapabilities, VoiceInfo
from infrastructure.audio.providers.tts.base import BaseTTSProvider

logger = logging.getLogger(__name__)


class VoiceCacheService:
    """Caches provider voices, capabilities, and health status."""

    def __init__(
        self,
        provider: BaseTTSProvider,
        *,
        voice_ttl: int = VOICE_CACHE_TTL_SECONDS,
        health_ttl: int = HEALTH_CACHE_TTL_SECONDS,
    ) -> None:
        self._provider = provider
        self._voice_ttl = voice_ttl
        self._health_ttl = health_ttl

    @property
    def _voice_key(self) -> str:
        return f"tts:{self._provider.provider_name}:voices"

    @property
    def _capabilities_key(self) -> str:
        return f"tts:{self._provider.provider_name}:capabilities"

    @property
    def _health_key(self) -> str:
        return f"tts:{self._provider.provider_name}:health"

    def get_voices(self, *, force_refresh: bool = False) -> list[VoiceInfo]:
        """Return cached voices or fetch from provider."""
        if not force_refresh:
            cached = cache.get(self._voice_key)
            if cached is not None:
                return list(cached)

        voices = self._provider.list_voices()
        cache.set(self._voice_key, voices, self._voice_ttl)
        logger.info(
            "TTS voices cached",
            extra={
                "event": "tts_voices_cached",
                "provider": self._provider.provider_name,
                "voice_count": len(voices),
            },
        )
        return voices

    def get_voice_ids(self, *, force_refresh: bool = False) -> set[str]:
        """Return cached provider voice identifiers."""
        voices = self.get_voices(force_refresh=force_refresh)
        return {voice.voice_id for voice in voices}

    def get_capabilities(self, *, force_refresh: bool = False) -> ProviderCapabilities:
        """Return cached provider capabilities."""
        if not force_refresh:
            cached = cache.get(self._capabilities_key)
            if isinstance(cached, ProviderCapabilities):
                return cached

        capabilities = self._provider.capabilities()
        cache.set(self._capabilities_key, capabilities, self._voice_ttl)
        return capabilities

    def is_healthy(self, *, force_refresh: bool = False) -> bool:
        """Return cached provider health status."""
        if not force_refresh:
            cached = cache.get(self._health_key)
            if cached is not None:
                return bool(cached)

        healthy = self._provider.health_check()
        cache.set(self._health_key, healthy, self._health_ttl)
        return healthy

    def invalidate(self) -> None:
        """Clear all cached provider data."""
        cache.delete(self._voice_key)
        cache.delete(self._capabilities_key)
        cache.delete(self._health_key)
