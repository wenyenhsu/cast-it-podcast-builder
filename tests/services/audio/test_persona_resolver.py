"""Tests for persona voice resolution."""

import pytest

from apps.scripts.models import Speaker
from domain.audio.exceptions import VoiceNotFoundException
from services.audio.persona_resolver import PersonaVoiceResolver


def test_resolve_expert_persona(voice_profiles: dict[str, object]) -> None:
    del voice_profiles
    resolver = PersonaVoiceResolver()
    profile = resolver.resolve(Speaker.EXPERT, provider="chatterbox", language="en")
    assert profile.name == "Expert Voice"
    assert profile.provider_voice_id == "expert.wav"


def test_resolve_missing_persona_raises(db: None) -> None:
    resolver = PersonaVoiceResolver()
    with pytest.raises(VoiceNotFoundException):
        resolver.resolve("expert", provider="chatterbox", language="en")
