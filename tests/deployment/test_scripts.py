"""Operational script smoke tests."""

from pathlib import Path


def test_operational_scripts_exist_and_are_executable() -> None:
    root = Path(__file__).resolve().parents[2] / "scripts"
    expected = [
        "build.sh",
        "start.sh",
        "stop.sh",
        "migrate.sh",
        "collectstatic.sh",
        "test.sh",
        "lint.sh",
        "format.sh",
        "create-admin.sh",
        "backup-db.sh",
        "verify-backup.sh",
    ]
    for name in expected:
        path = root / name
        assert path.exists(), f"Missing script: {name}"
        assert path.stat().st_mode & 0o111, f"Script not executable: {name}"
