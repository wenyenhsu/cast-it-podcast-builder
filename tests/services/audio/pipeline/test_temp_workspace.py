"""Tests for temp workspace cleanup."""

from pathlib import Path

from services.audio.pipeline.temp_workspace import TempWorkspace


def test_temp_workspace_cleanup(tmp_path: Path) -> None:
    import uuid

    episode_id = uuid.uuid4()
    workspace = TempWorkspace(episode_id, base_dir=tmp_path)
    with workspace:
        temp_file = workspace.file("test.wav")
        temp_file.write_bytes(b"data")
        assert workspace.path.exists()

    assert not workspace.path.exists()


def test_temp_workspace_idempotent_cleanup(tmp_path: Path) -> None:
    import uuid

    episode_id = uuid.uuid4()
    workspace = TempWorkspace(episode_id, base_dir=tmp_path)
    with workspace:
        path = workspace.path
    workspace.cleanup()
    workspace.cleanup()
    assert not path.exists()
