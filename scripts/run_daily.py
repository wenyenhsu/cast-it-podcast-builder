"""Run the full daily pipeline chain once, exactly as Celery Beat would.

Used by scripts/morning-catchup.ps1 to recover mornings the scheduler
missed (machine off/asleep/crashed during the 6:00-9:15 window). Safe to
re-run: import dedupes articles and publishing upserts.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
BASE = "http://localhost:8000/api/v1"

STAGES = [
    ("import_news", "apps.scheduler.tasks.import_news", "import_news_scheduled"),
    ("episode_planning", "apps.scheduler.tasks.planning", "episode_planning_scheduled"),
    ("generate_script", "apps.scheduler.tasks.script", "generate_script_scheduled"),
    ("generate_audio", "apps.scheduler.tasks.audio", "generate_audio_scheduled"),
    ("publish_episode", "apps.scheduler.tasks.publish", "publish_episode_scheduled"),
]


def api(path: str):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
        return json.loads(r.read().decode())


def newest_job(job_type: str):
    data = api(f"/jobs/?job_type={job_type}&ordering=-created_at&page_size=1")
    results = data.get("results", [])
    return results[0] if results else None


def dispatch(module: str, func: str) -> None:
    code = f"from {module} import {func}; r = {func}.delay(); print('sent', r.id)"
    subprocess.run(
        ["docker", "compose", "exec", "-T", "web",
         "python", "manage.py", "shell", "-c", code],
        check=True, capture_output=True, text=True, cwd=REPO,
    )


def wait_stage(job_type: str, before_id: str | None, timeout_s: int = 3600) -> bool:
    start = time.time()
    while time.time() - start < timeout_s:
        job = newest_job(job_type)
        if job and job["id"] != before_id:
            if job["status"] in ("succeeded", "failed", "cancelled"):
                print(f"[{job_type}] {job['status']}")
                return job["status"] == "succeeded"
        time.sleep(15)
    print(f"[{job_type}] timed out")
    return False


def main() -> int:
    for job_type, module, func in STAGES:
        prev = newest_job(job_type)
        prev_id = prev["id"] if prev else None
        print(f"--- dispatching {job_type}")
        dispatch(module, func)
        if not wait_stage(job_type, prev_id):
            return 1

    print("--- dispatching publish_supabase")
    code = ("from apps.scheduler.tasks.publish import publish_supabase_scheduled; "
            "print(publish_supabase_scheduled())")
    out = subprocess.run(
        ["docker", "compose", "exec", "-T", "web",
         "python", "manage.py", "shell", "-c", code],
        capture_output=True, text=True, cwd=REPO,
    )
    tail = out.stdout.strip().splitlines()
    print(tail[-1] if tail else out.stderr[-300:])
    print("DAILY RUN COMPLETE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
