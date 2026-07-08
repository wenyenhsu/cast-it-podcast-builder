"""Tests for the Supabase episode publisher."""

from pathlib import Path

import pytest

from apps.audio.models import AudioAsset, AudioAssetStatus
from apps.episodes.models import Episode
from services.publish.supabase_publisher import (
    SupabasePublisher,
    SupabaseSettings,
)


class FakeResponse:
    def __init__(self, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text


class FakeHTTPClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.requests.append({"url": url, **kwargs})
        return FakeResponse(200)


@pytest.fixture
def supabase_settings() -> SupabaseSettings:
    return SupabaseSettings(
        url="https://example.supabase.co",
        service_role_key="secret",
        audio_bucket="episode-audio",
    )


@pytest.fixture
def episode_with_audio(tmp_path: Path, settings) -> Episode:
    settings.MEDIA_ROOT = str(tmp_path)
    audio_file = tmp_path / "audio" / "final.mp3"
    audio_file.parent.mkdir(parents=True)
    audio_file.write_bytes(b"mp3-bytes")

    episode = Episode.objects.create(title="Ep", duration_seconds=120)
    AudioAsset.objects.create(
        episode=episode,
        provider="ffmpeg",
        voice="",
        file_path="audio/final.mp3",
        format="mp3",
        is_final_episode_audio=True,
        status=AudioAssetStatus.READY,
        duration=120,
    )
    return episode


@pytest.mark.django_db
def test_publish_episode_uploads_audio_and_upserts_row(
    supabase_settings: SupabaseSettings,
    episode_with_audio: Episode,
) -> None:
    http = FakeHTTPClient()
    publisher = SupabasePublisher(settings=supabase_settings, http_client=http)

    result = publisher.publish_episode(episode_with_audio)

    upload, upsert = http.requests
    assert upload["url"] == (
        "https://example.supabase.co/storage/v1/object/"
        "episode-audio/audio/final.mp3"
    )
    assert upload["content"] == b"mp3-bytes"
    assert upsert["url"].startswith(
        "https://example.supabase.co/rest/v1/episodes"
    )
    row = upsert["json"][0]
    assert row["id"] == str(episode_with_audio.id)
    assert row["audio_url"] == result.audio_url
    assert result.audio_url.endswith("/public/episode-audio/audio/final.mp3")


@pytest.mark.django_db
def test_publish_episode_without_final_audio_raises(
    supabase_settings: SupabaseSettings,
) -> None:
    episode = Episode.objects.create(title="No audio")
    publisher = SupabasePublisher(
        settings=supabase_settings, http_client=FakeHTTPClient()
    )
    with pytest.raises(ValueError, match="no final ready audio"):
        publisher.publish_episode(episode)


def test_settings_validation_requires_url_and_key() -> None:
    with pytest.raises(ValueError):
        SupabasePublisher(
            settings=SupabaseSettings(url="", service_role_key="", audio_bucket="b"),
            http_client=FakeHTTPClient(),
        )
