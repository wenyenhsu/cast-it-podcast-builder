"""Tests for default voice profile bootstrap."""

from unittest.mock import MagicMock, patch

import pytest

from apps.audio.models import PersonaVoiceMapping, VoiceProfile
from apps.scripts.models import Speaker
from domain.audio.dtos import VoiceInfo
from services.audio.settings import TTSSettings
from services.audio.voice_setup import VoiceSetupService


@pytest.mark.django_db
def test_ensure_defaults_creates_distinct_profiles_and_mappings() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=30.0,
        default_voice="intro.wav",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )
    voices = [
        VoiceInfo(voice_id="intro.wav", name="Intro"),
        VoiceInfo(voice_id="expert.wav", name="Expert"),
        VoiceInfo(voice_id="beginner.wav", name="Beginner"),
    ]

    with patch(
        "services.audio.voice_setup.TTSProviderFactory.create",
        return_value=MagicMock(list_voices=MagicMock(return_value=voices)),
    ):
        VoiceSetupService().ensure_defaults(settings)

    intro = VoiceProfile.objects.get(name="chatterbox-intro")
    expert = VoiceProfile.objects.get(name="chatterbox-expert")
    beginner = VoiceProfile.objects.get(name="chatterbox-beginner")

    assert intro.provider_voice_id == "intro.wav"
    assert expert.provider_voice_id == "expert.wav"
    assert beginner.provider_voice_id == "beginner.wav"

    assert PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.INTRO,
    ).voice_profile == intro
    assert PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.EXPERT,
    ).voice_profile == expert
    assert PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.BEGINNER,
    ).voice_profile == beginner
    assert PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.NARRATION,
    ).voice_profile == expert
    assert PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.OUTRO,
    ).voice_profile == beginner


@pytest.mark.django_db
def test_ensure_defaults_does_not_overwrite_existing_mapping() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=30.0,
        default_voice="intro.wav",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )
    custom_profile = VoiceProfile.objects.create(
        name="Custom Expert Voice",
        provider="chatterbox",
        provider_voice_id="custom-expert.wav",
        enabled=True,
    )
    PersonaVoiceMapping.objects.create(
        persona=Speaker.EXPERT,
        provider="chatterbox",
        voice_profile=custom_profile,
        enabled=True,
    )

    voices = [
        VoiceInfo(voice_id="intro.wav", name="Intro"),
        VoiceInfo(voice_id="expert.wav", name="Expert"),
        VoiceInfo(voice_id="beginner.wav", name="Beginner"),
    ]

    with patch(
        "services.audio.voice_setup.TTSProviderFactory.create",
        return_value=MagicMock(list_voices=MagicMock(return_value=voices)),
    ):
        VoiceSetupService().ensure_defaults(settings)

    mapping = PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.EXPERT,
    )
    assert mapping.voice_profile == custom_profile


@pytest.mark.django_db
def test_ensure_defaults_migrates_legacy_default_mapping() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=30.0,
        default_voice="intro.wav",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )
    legacy_profile = VoiceProfile.objects.create(
        name="chatterbox-default",
        provider="chatterbox",
        provider_voice_id="intro.wav",
        enabled=True,
    )
    PersonaVoiceMapping.objects.create(
        persona=Speaker.EXPERT,
        provider="chatterbox",
        voice_profile=legacy_profile,
        enabled=True,
    )

    voices = [
        VoiceInfo(voice_id="intro.wav", name="Intro"),
        VoiceInfo(voice_id="expert.wav", name="Expert"),
        VoiceInfo(voice_id="beginner.wav", name="Beginner"),
    ]

    with patch(
        "services.audio.voice_setup.TTSProviderFactory.create",
        return_value=MagicMock(list_voices=MagicMock(return_value=voices)),
    ):
        VoiceSetupService().ensure_defaults(settings)

    expert_profile = VoiceProfile.objects.get(name="chatterbox-expert")
    mapping = PersonaVoiceMapping.objects.get(
        provider="chatterbox",
        persona=Speaker.EXPERT,
    )
    assert mapping.voice_profile == expert_profile


@pytest.mark.django_db
def test_ensure_defaults_uses_env_persona_voices() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=30.0,
        default_voice="",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
        persona_voices={
            Speaker.INTRO: "Abigail.wav",
            Speaker.EXPERT: "Connor.wav",
            Speaker.BEGINNER: "Emily.wav",
        },
    )

    with patch(
        "services.audio.voice_setup.TTSProviderFactory.create",
        return_value=MagicMock(list_voices=MagicMock(return_value=[])),
    ):
        VoiceSetupService().ensure_defaults(settings)

    assert VoiceProfile.objects.get(name="chatterbox-intro").provider_voice_id == "Abigail.wav"
    assert VoiceProfile.objects.get(name="chatterbox-expert").provider_voice_id == "Connor.wav"
    assert (
        VoiceProfile.objects.get(name="chatterbox-beginner").provider_voice_id
        == "Emily.wav"
    )


@pytest.mark.django_db
def test_ensure_defaults_resyncs_shared_auto_managed_mapping() -> None:
    settings = TTSSettings(
        provider="chatterbox",
        base_url="http://localhost:8004",
        timeout=30.0,
        default_voice="intro.wav",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
        persona_voices={
            Speaker.INTRO: "intro.wav",
            Speaker.EXPERT: "expert.wav",
            Speaker.BEGINNER: "beginner.wav",
        },
    )
    shared_profile = VoiceProfile.objects.create(
        name="chatterbox-default",
        provider="chatterbox",
        provider_voice_id="intro.wav",
        enabled=True,
    )
    for persona in (Speaker.INTRO, Speaker.EXPERT, Speaker.BEGINNER):
        PersonaVoiceMapping.objects.create(
            persona=persona,
            provider="chatterbox",
            voice_profile=shared_profile,
            enabled=True,
        )

    with patch(
        "services.audio.voice_setup.TTSProviderFactory.create",
        return_value=MagicMock(list_voices=MagicMock(return_value=[])),
    ):
        VoiceSetupService().ensure_defaults(settings)

    intro = VoiceProfile.objects.get(name="chatterbox-intro")
    expert = VoiceProfile.objects.get(name="chatterbox-expert")
    beginner = VoiceProfile.objects.get(name="chatterbox-beginner")
    assert PersonaVoiceMapping.objects.get(persona=Speaker.INTRO).voice_profile == intro
    assert PersonaVoiceMapping.objects.get(persona=Speaker.EXPERT).voice_profile == expert
    assert (
        PersonaVoiceMapping.objects.get(persona=Speaker.BEGINNER).voice_profile
        == beginner
    )
