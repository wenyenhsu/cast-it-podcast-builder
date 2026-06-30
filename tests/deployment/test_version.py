"""Build metadata tests."""

import pytest

from infrastructure.deployment.version import BuildMetadata, get_build_metadata


def test_build_metadata_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_VERSION", "1.2.3")
    monkeypatch.setenv("BUILD_GIT_COMMIT", "abc1234")
    monkeypatch.setenv("BUILD_NUMBER", "99")
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("IMAGE_TAG", "staging-99")
    metadata = get_build_metadata()
    assert metadata.version == "1.2.3"
    assert metadata.git_commit == "abc1234"
    assert metadata.build_number == "99"
    assert metadata.environment == "staging"
    assert metadata.image_tag == "staging-99"


def test_build_metadata_as_dict() -> None:
    metadata = BuildMetadata(
        version="0.1.0",
        git_commit="deadbeef",
        build_number="1",
        environment="production",
        release_timestamp="2026-01-01T00:00:00+00:00",
        image_tag="v0.1.0",
    )
    payload = metadata.as_dict()
    assert payload["version"] == "0.1.0"
    assert payload["git_commit"] == "deadbeef"
