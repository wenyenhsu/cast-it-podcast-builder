"""Tests for operations script views."""

from unittest.mock import patch

import pytest
from django.urls import reverse

from apps.episodes.models import Episode, EpisodeStatus
from apps.scheduler.models import Job, JobType
from apps.scripts.models import Script, ScriptSegment, ScriptStatus, Speaker
from apps.audio.models import AudioAsset, AudioAssetStatus
from services.admin.dispatch import AdminJobDispatchService


@pytest.mark.django_db
def test_scripts_page_redirects_to_content_tab(admin_client) -> None:
    response = admin_client.get(reverse("operations:scripts"))
    assert response.status_code == 302
    assert "view=scripts" in response.url


@pytest.mark.django_db
def test_manual_script_page_still_renders_without_scripts_tab(
    admin_client,
) -> None:
    response = admin_client.get(reverse("operations:content"), {"view": "scripts"})
    assert response.status_code == 200
    content = response.content.decode()
    assert "Add Manual Script" in content
    assert "Save Manual Script" in content
    assert ">Scripts</a>" not in content


@pytest.mark.django_db
def test_scripts_page_shows_manual_script_form(admin_client) -> None:
    response = admin_client.get(
        reverse("operations:content"),
        {"view": "scripts"},
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Add Manual Script" in content
    assert "Save Manual Script" in content


@pytest.mark.django_db
def test_create_manual_script_from_scripts_ui(admin_client) -> None:
    response = admin_client.post(
        reverse("operations:scripts"),
        {
            "script_action": "create_manual_script",
            "script_title": "TTS Ready Script",
            "script_dialogue": "intro: Welcome.\nexpert: News update.",
        },
    )
    assert response.status_code == 302
    script = Script.objects.get(title="TTS Ready Script")
    assert script.status == ScriptStatus.READY
    assert script.segments.count() == 2
    assert response.url == reverse("operations:script_detail", args=[script.pk])


@pytest.mark.django_db
def test_enqueue_coerces_uuid_payload_values() -> None:
    import uuid
    from unittest.mock import MagicMock, patch

    from services.admin.dispatch import AdminJobDispatchService

    task = MagicMock()
    task.delay.return_value = MagicMock(id="celery-id")
    script_id = uuid.uuid4()
    with patch(
        "api.v1.services.job_dispatch.get_task_for_job_type",
        return_value=task,
    ):
        job = AdminJobDispatchService().generate_audio(
            str(uuid.uuid4()),
            script_id=str(script_id),
        )

    assert job.payload["script_id"] == str(script_id)


@pytest.mark.django_db
def test_script_detail_generate_audio_action(admin_client) -> None:
    episode = Episode.objects.create(title="Audio Episode", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Ready Script",
        status=ScriptStatus.READY,
    )
    ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.NARRATION,
        text="Ready for TTS.",
    )
    job = Job.objects.create(
        job_type=JobType.GENERATE_AUDIO,
        payload={"script_id": str(script.id)},
    )

    with patch.object(AdminJobDispatchService, "generate_audio", return_value=job):
        response = admin_client.post(
            reverse("operations:script_detail", args=[script.pk]),
            {"script_action": "generate_audio"},
        )

    assert response.status_code == 302
    response = admin_client.get(
        f"{reverse('operations:script_detail', args=[script.pk])}?job={job.id}",
        follow=True,
    )
    assert b"TTS audio generation queued" in response.content


@pytest.mark.django_db
def test_content_shows_tts_generation_link_when_script_ready(admin_client) -> None:
    episode = Episode.objects.create(title="Audio Episode", status=EpisodeStatus.DRAFT)
    Script.objects.create(
        episode=episode,
        version=1,
        title="Ready Script",
        status=ScriptStatus.READY,
    )
    response = admin_client.get(reverse("operations:content"))
    content = response.content.decode()
    assert "TTS Generation" in content
    assert reverse("operations:tts_generation") in content


@pytest.mark.django_db
def test_tts_generation_for_script(admin_client) -> None:
    episode = Episode.objects.create(title="Audio Episode", status=EpisodeStatus.DRAFT)
    ready = Script.objects.create(
        episode=episode,
        version=1,
        title="Ready Script",
        status=ScriptStatus.READY,
    )
    failed = Script.objects.create(
        episode=episode,
        version=2,
        title="Failed Script",
        status=ScriptStatus.FAILED,
    )
    response = admin_client.get(
        reverse("operations:tts_generation"),
        {"script": str(failed.id)},
    )
    assert response.status_code == 302
    assert response.url == reverse("operations:script_detail", args=[failed.pk])

    response = admin_client.get(
        reverse("operations:tts_generation"),
        {"script": str(ready.id)},
    )
    assert response.status_code == 302
    assert response.url == reverse("operations:script_detail", args=[ready.pk])


@pytest.mark.django_db
def test_tts_generation_for_episode(admin_client) -> None:
    episode = Episode.objects.create(title="Audio Episode", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Ready Script",
        status=ScriptStatus.READY,
    )
    response = admin_client.get(
        reverse("operations:tts_generation"),
        {"episode": str(episode.id)},
    )
    assert response.status_code == 302
    assert response.url == reverse("operations:script_detail", args=[script.pk])


@pytest.mark.django_db
def test_episodes_view_lists_generate_tts_button(admin_client) -> None:
    episode = Episode.objects.create(
        title="Waiting Episode",
        status=EpisodeStatus.GENERATING_SCRIPT,
    )
    response = admin_client.get(
        reverse("operations:content"),
        {"view": "episodes"},
    )
    content = response.content.decode()
    assert "Generate TTS" in content
    assert episode.title in content


@pytest.mark.django_db
def test_tts_generation_redirects_to_ready_script(admin_client) -> None:
    episode = Episode.objects.create(title="Audio Episode", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Ready Script",
        status=ScriptStatus.READY,
    )
    response = admin_client.get(reverse("operations:tts_generation"))
    assert response.status_code == 302
    assert response.url == reverse("operations:script_detail", args=[script.pk])


@pytest.mark.django_db
def test_delete_script_from_scripts_ui(admin_client) -> None:
    episode = Episode.objects.create(title="Remove Me", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=2,
        title="Failed attempt",
        status=ScriptStatus.FAILED,
    )
    response = admin_client.post(
        reverse("operations:content"),
        {
            "script_action": "delete_episode",
            "script_id": str(script.id),
            "episode_id": str(episode.id),
        },
    )
    assert response.status_code == 302
    assert "view=scripts" in response.url
    assert not Script.objects.filter(pk=script.id).exists()
    assert not Episode.objects.filter(pk=episode.id).exists()


@pytest.mark.django_db
def test_episodes_list_page(admin_client) -> None:
    episode = Episode.objects.create(title="Test Episode", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Morning Brief",
        status=ScriptStatus.READY,
    )
    ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.EXPERT,
        text="Welcome to the show.",
    )

    response = admin_client.get(
        reverse("operations:content"),
        {"view": "episodes"},
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Test Episode" in content
    assert "Generate TTS" in content
    assert "Delete" in content


@pytest.mark.django_db
def test_episodes_list_filtered_by_search(admin_client) -> None:
    Episode.objects.create(title="Filtered Episode", status=EpisodeStatus.DRAFT)
    Episode.objects.create(title="Other Show", status=EpisodeStatus.DRAFT)

    response = admin_client.get(
        reverse("operations:content"),
        {"view": "episodes", "q": "Filtered"},
    )
    content = response.content.decode()
    assert "Filtered Episode" in content
    assert "Other Show" not in content


@pytest.mark.django_db
def test_script_detail_plays_generated_audio(admin_client, tmp_path, settings) -> None:
    settings.MEDIA_ROOT = tmp_path
    episode = Episode.objects.create(title="Audio Episode", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Ready Script",
        status=ScriptStatus.READY,
    )
    segment = ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.NARRATION,
        text="Ready for TTS.",
    )
    audio_dir = tmp_path / "audio" / str(episode.id)
    audio_dir.mkdir(parents=True)
    audio_file = audio_dir / "segment_001.wav"
    audio_file.write_bytes(b"RIFFxxxxWAVEfmt ")

    asset = AudioAsset.objects.create(
        episode=episode,
        script_segment=segment,
        file_path=f"audio/{episode.id}/segment_001.wav",
        status=AudioAssetStatus.READY,
        format="wav",
        duration=3,
    )

    detail = admin_client.get(reverse("operations:script_detail", args=[script.pk]))
    assert detail.status_code == 200
    content = detail.content.decode()
    assert "TTS Audio" in content
    assert reverse("operations:audio_asset", args=[asset.pk]) in content
    assert "<audio" in content

    audio = admin_client.get(reverse("operations:audio_asset", args=[asset.pk]))
    assert audio.status_code == 200
    assert audio["Content-Type"].startswith("audio/")


@pytest.mark.django_db
def test_script_detail_page(admin_client) -> None:
    episode = Episode.objects.create(title="Detail Episode", status=EpisodeStatus.DRAFT)
    script = Script.objects.create(
        episode=episode,
        version=1,
        title="Detail Script",
        status=ScriptStatus.READY,
        llm_provider="ollama",
        model_name="gemma3:12b",
    )
    ScriptSegment.objects.create(
        script=script,
        sequence=1,
        speaker=Speaker.BEGINNER,
        text="Can you explain that simply?",
    )

    response = admin_client.get(
        reverse("operations:script_detail", args=[script.pk]),
    )
    assert response.status_code == 200
    content = response.content.decode()
    assert "Detail Script" in content
    assert "Can you explain that simply?" in content
    assert "Dialogue" in content
