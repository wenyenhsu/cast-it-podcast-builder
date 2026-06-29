"""Tests for TTS provider factory and settings."""

from services.audio.provider_factory import TTSProviderFactory
from services.audio.settings import TTSSettings


def test_settings_to_provider_config() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=60.0,
        default_voice="expert.wav",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )
    config = settings.to_provider_config()
    assert config.base_url == "http://localhost:8004"
    assert config.audio_format == "wav"


def test_factory_creates_chatterbox_provider() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=60.0,
        default_voice="",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )
    provider = TTSProviderFactory(settings).create()
    assert provider.provider_name == "chatterbox"
