"""Tests for default voice profile bootstrap."""

import pytest

from apps.audio.models import PersonaVoiceMapping, VoiceProfile
from apps.scripts.models import Speaker
from services.audio.settings import TTSSettings
from services.audio.voice_setup import VoiceSetupService


@pytest.mark.django_db
def test_ensure_defaults_creates_profile_and_mappings() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=30.0,
        default_voice="demo-voice",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )
    VoiceSetupService().ensure_defaults(settings)

    profile = VoiceProfile.objects.get(name="chatterbox-default")
    assert profile.provider_voice_id == "demo-voice"
    assert PersonaVoiceMapping.objects.filter(
        provider="chatterbox",
        persona=Speaker.NARRATION,
        voice_profile=profile,
        enabled=True,
    ).exists()
