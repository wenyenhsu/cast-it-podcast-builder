"""Tests for voice cache service."""

from django.core.cache import cache

from infrastructure.audio.providers.tts.chatterbox import ChatterboxProvider
from services.audio.voice_cache import VoiceCacheService


def test_voice_cache_stores_provider_voices(
    chatterbox_provider: ChatterboxProvider,
) -> None:
    cache.clear()
    service = VoiceCacheService(chatterbox_provider, voice_ttl=60, health_ttl=60)

    first = service.get_voices()
    second = service.get_voices()

    assert len(first) == 2
    assert first == second
    assert service.get_voice_ids() == {"expert.wav", "beginner.wav"}


def test_voice_cache_health(chatterbox_provider: ChatterboxProvider) -> None:
    cache.clear()
    service = VoiceCacheService(chatterbox_provider)
    assert service.is_healthy() is True
