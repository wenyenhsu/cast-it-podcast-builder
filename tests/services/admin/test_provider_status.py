"""Tests for the provider dashboard service."""

import pytest

from services.admin.provider_status import ProviderDashboardService


@pytest.mark.django_db
def test_llm_and_tts_status_are_separate(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.admin.provider_status.LLMProviderFactory.create",
        lambda self: type(
            "P",
            (),
            {"health_check": lambda s: True, "list_models": lambda s: []},
        )(),
    )
    monkeypatch.setattr(
        "services.admin.provider_status.TTSProviderFactory.create",
        lambda self: type("P", (), {"health_check": lambda s: True})(),
    )

    service = ProviderDashboardService()
    llm = service.llm_status()
    tts = service.tts_status()

    assert llm["name"] == "LLM"
    assert llm["provider_type"] == "llm"
    assert "chat_model" in llm
    assert "embedding_model" in llm

    assert tts["name"] == "TTS"
    assert tts["provider_type"] == "tts"
    assert "default_voice" in tts
    assert "audio_format" in tts

    snapshot = service.snapshot()
    assert len(snapshot) == 2
