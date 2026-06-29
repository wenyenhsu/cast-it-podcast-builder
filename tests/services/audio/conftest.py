"""Shared fixtures for audio service tests."""

import io
import wave
from pathlib import Path

import pytest
from django.utils import timezone

from apps.articles.models import Article, ArticleStatus
from apps.audio.models import PersonaVoiceMapping, VoiceProfile
from apps.episodes.models import Episode, EpisodeArticle, EpisodeStatus
from apps.providers.models import NewsSource, ProviderType
from apps.scripts.models import Script, ScriptSegment, ScriptStatus, Speaker
from domain.audio.config import TTSProviderConfig
from infrastructure.audio.providers.tts.chatterbox import ChatterboxProvider
from services.audio.settings import TTSSettings


def build_wav_bytes(
    *,
    duration_seconds: float = 1.0,
    sample_rate: int = 22050,
) -> bytes:
    """Build minimal WAV bytes for provider tests."""
    frame_count = int(sample_rate * duration_seconds)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00\x00" * frame_count)
    return buffer.getvalue()


class MockHTTPResponse:
    """Minimal HTTP response stub."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        content: bytes = b"",
        json_data: object = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self.content = content
        self._json_data = json_data
        self.text = text

    def json(self) -> object:
        return self._json_data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class MockHTTPClient:
    """Mock HTTP client for Chatterbox provider tests."""

    def __init__(self) -> None:
        self.post_calls: list[dict[str, object]] = []
        self.get_calls: list[str] = []

    def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        timeout: float,
    ) -> MockHTTPResponse:
        self.post_calls.append({"url": url, "json": json, "timeout": timeout})
        return MockHTTPResponse(content=build_wav_bytes())

    def get(self, url: str, *, timeout: float) -> MockHTTPResponse:
        self.get_calls.append(url)
        if url.endswith("/get_predefined_voices"):
            return MockHTTPResponse(
                json_data=[
                    {"display_name": "Expert Voice", "filename": "expert.wav"},
                    {"display_name": "Beginner Voice", "filename": "beginner.wav"},
                ]
            )
        if url.endswith("/api/model-info"):
            return MockHTTPResponse(
                json_data={"supported_languages": ["en", "es"]},
            )
        return MockHTTPResponse(json_data={})


@pytest.fixture
def tts_config() -> TTSProviderConfig:
    return TTSProviderConfig(
        base_url="http://chatterbox.test",
        timeout=30.0,
        default_voice="expert.wav",
        audio_format="wav",
    )


@pytest.fixture
def mock_http_client() -> MockHTTPClient:
    return MockHTTPClient()


@pytest.fixture
def chatterbox_provider(
    tts_config: TTSProviderConfig,
    mock_http_client: MockHTTPClient,
    tmp_path: Path,
) -> ChatterboxProvider:
    return ChatterboxProvider(
        config=tts_config,
        http_client=mock_http_client,
        temp_dir=tmp_path,
    )


@pytest.fixture
def tts_settings() -> TTSSettings:
    return TTSSettings(
        provider="chatterbox",
        base_url="http://chatterbox.test",
        timeout=30.0,
        default_voice="expert.wav",
        audio_format="wav",
        max_text_length=5000,
        words_per_minute=150,
        storage_subdir="audio",
    )


@pytest.fixture
def voice_profiles(db: None) -> dict[str, VoiceProfile]:
    expert = VoiceProfile.objects.create(
        name="Expert Voice",
        provider="chatterbox",
        provider_voice_id="expert.wav",
        language="en",
        gender="neutral",
        default_speed=1.0,
        enabled=True,
    )
    beginner = VoiceProfile.objects.create(
        name="Beginner Voice",
        provider="chatterbox",
        provider_voice_id="beginner.wav",
        language="en",
        gender="neutral",
        default_speed=1.0,
        enabled=True,
    )
    PersonaVoiceMapping.objects.create(
        persona=Speaker.EXPERT,
        voice_profile=expert,
        provider="chatterbox",
        enabled=True,
    )
    PersonaVoiceMapping.objects.create(
        persona=Speaker.BEGINNER,
        voice_profile=beginner,
        provider="chatterbox",
        enabled=True,
    )
    return {"expert": expert, "beginner": beginner}


@pytest.fixture
def ready_script(voice_profiles: dict[str, VoiceProfile]) -> Script:
    del voice_profiles
    source = NewsSource.objects.create(
        name="Tech Feed",
        provider_type=ProviderType.RSS,
        enabled=True,
    )
    article = Article.objects.create(
        source=source,
        title="AI News",
        url="https://example.com/ai",
        published_at=timezone.now(),
        content_hash="hash-audio-test",
        status=ArticleStatus.SELECTED,
    )
    episode = Episode.objects.create(
        title="Weekly AI",
        summary="Summary",
        language="en",
        status=EpisodeStatus.GENERATING_SCRIPT,
    )
    EpisodeArticle.objects.create(episode=episode, article=article)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Weekly AI Script",
        status=ScriptStatus.READY,
    )
    ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.EXPERT,
        voice="expert_voice",
        emotion="calm",
        text="Welcome to the show about artificial intelligence today.",
    )
    ScriptSegment.objects.create(
        script=script,
        sequence=2,
        speaker=Speaker.BEGINNER,
        voice="beginner_voice",
        emotion="curious",
        text="Can you explain what happened in AI this week?",
    )
    return script
