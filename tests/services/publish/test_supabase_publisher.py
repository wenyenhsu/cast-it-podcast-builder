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
    def __init__(self, get_status: int = 200) -> None:
        self.requests: list[dict] = []
        self.get_status = get_status

    def get(self, url: str, **kwargs) -> FakeResponse:
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return FakeResponse(self.get_status)

    def post(self, url: str, **kwargs) -> FakeResponse:
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return FakeResponse(200)

    def delete(self, url: str, **kwargs) -> FakeResponse:
        self.requests.append({"method": "DELETE", "url": url, **kwargs})
        return FakeResponse(204)


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

    upload, upsert, tag_delete, chapter_delete = http.requests
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
    assert tag_delete["method"] == "DELETE"
    assert f"episode_id=eq.{episode_with_audio.id}" in tag_delete["url"]
    assert chapter_delete["method"] == "DELETE"
    assert "/rest/v1/chapters" in chapter_delete["url"]


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


@pytest.mark.django_db
def test_episode_tags_pushed_from_taxonomy_articles(
    supabase_settings: SupabaseSettings,
    episode_with_audio: Episode,
) -> None:
    from apps.articles.models import Article, ArticleTag, Tag
    from apps.episodes.models import EpisodeArticle
    from apps.providers.models import NewsSource, ProviderType

    source = NewsSource.objects.create(name="s", provider_type=ProviderType.RSS)
    article = Article.objects.create(
        source=source, title="a", url="https://x/a", content="c"
    )
    EpisodeArticle.objects.create(episode=episode_with_audio, article=article)
    for slug, name in [("llm", "LLM"), ("security", "Security"), ("legacy-junk", "Legacy Junk")]:
        tag = Tag.objects.create(slug=slug, name=name)
        ArticleTag.objects.create(article=article, tag=tag)

    http = FakeHTTPClient()
    SupabasePublisher(settings=supabase_settings, http_client=http).publish_episode(
        episode_with_audio
    )

    tag_insert = next(
        r
        for r in http.requests
        if r["method"] == "POST" and r["url"].endswith("/rest/v1/episode_tags")
    )
    slugs = {r["tag_slug"] for r in tag_insert["json"]}
    assert slugs == {"llm", "security"}  # legacy tag filtered out


@pytest.mark.django_db
def test_chapters_uploaded_and_upserted(
    supabase_settings: SupabaseSettings,
    episode_with_audio: Episode,
    tmp_path: Path,
) -> None:
    from apps.articles.models import Article, ArticleTag, Tag
    from apps.episodes.models import EpisodeArticle
    from apps.providers.models import NewsSource, ProviderType

    source = NewsSource.objects.create(name="s", provider_type=ProviderType.RSS)
    article = Article.objects.create(
        source=source,
        title="Chapter story",
        url="https://x/ch",
        content="c",
        summary="chapter summary",
        category="AI",
    )
    EpisodeArticle.objects.create(episode=episode_with_audio, article=article)
    tag = Tag.objects.create(slug="llm", name="LLM")
    ArticleTag.objects.create(article=article, tag=tag)

    chapter_file = tmp_path / "audio" / "chapter_01.mp3"
    chapter_file.write_bytes(b"chapter-bytes")
    chapter_asset = AudioAsset.objects.create(
        episode=episode_with_audio,
        article=article,
        provider="ffmpeg",
        file_path="audio/chapter_01.mp3",
        format="mp3",
        is_final_episode_audio=False,
        status=AudioAssetStatus.READY,
        duration=180,
    )

    http = FakeHTTPClient()
    SupabasePublisher(settings=supabase_settings, http_client=http).publish_episode(
        episode_with_audio
    )

    chapter_upsert = next(
        r
        for r in http.requests
        if r["method"] == "POST" and "/rest/v1/chapters" in r["url"]
    )
    row = chapter_upsert["json"][0]
    assert row["id"] == str(chapter_asset.id)
    assert row["article_id"] == str(article.id)
    assert row["title"] == "Chapter story"
    assert row["audio_url"].endswith("/public/episode-audio/audio/chapter_01.mp3")

    chapter_tags = next(
        r
        for r in http.requests
        if r["method"] == "POST" and r["url"].endswith("/rest/v1/chapter_tags")
    )
    assert chapter_tags["json"] == [
        {"chapter_id": str(chapter_asset.id), "tag_slug": "llm"}
    ]


def test_sync_taxonomy_upserts_all_allowed_tags(
    supabase_settings: SupabaseSettings,
) -> None:
    from domain.intelligence.constants import ALLOWED_TAGS

    http = FakeHTTPClient()
    count = SupabasePublisher(
        settings=supabase_settings, http_client=http
    ).sync_taxonomy()

    assert count == len(ALLOWED_TAGS)
    request = http.requests[-1]
    assert request["url"].endswith("/rest/v1/tags?on_conflict=slug")
    names = {row["name"] for row in request["json"]}
    assert names == set(ALLOWED_TAGS)
    assert {row["slug"] for row in request["json"]} >= {"llm", "claude-fable", "uiux"}


def test_probe_health_ok(supabase_settings: SupabaseSettings) -> None:
    http = FakeHTTPClient(get_status=200)
    probe = SupabasePublisher(
        settings=supabase_settings,
        http_client=http,
    ).probe_health()
    assert probe.healthy is True
    assert probe.configured is True
    assert http.requests[0]["url"].endswith("/rest/v1/tags?select=slug&limit=1")


def test_probe_health_not_configured() -> None:
    settings = SupabaseSettings(url="", service_role_key="", audio_bucket="episode-audio")
    probe = SupabasePublisher(
        settings=settings,
        http_client=FakeHTTPClient(),
        require_config=False,
    ).probe_health()
    assert probe.healthy is False
    assert probe.configured is False
    assert probe.detail == "Not configured"


def test_probe_health_rest_error(supabase_settings: SupabaseSettings) -> None:
    http = FakeHTTPClient(get_status=503)
    probe = SupabasePublisher(
        settings=supabase_settings,
        http_client=http,
    ).probe_health()
    assert probe.healthy is False
    assert "503" in probe.detail
