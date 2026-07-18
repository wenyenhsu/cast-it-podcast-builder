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
    # generate_script is dispatched separately: the handler requires an
    # explicit episode_id (automatic scheduling was disabled in favor of
    # the Content UI; this driver supplies the id programmatically).
    ("generate_audio", "apps.scheduler.tasks.audio", "generate_audio_scheduled"),
    ("publish_episode", "apps.scheduler.tasks.publish", "publish_episode_scheduled"),
]


def api(path: str):
    last_error: Exception | None = None
    for _ in range(5):
        try:
            with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as r:
                return json.loads(r.read().decode())
        except Exception as exc:  # transient: container restarts, reloads
            last_error = exc
            time.sleep(10)
    raise last_error  # type: ignore[misc]


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


def newest_episode_id() -> str | None:
    data = api("/episodes/?ordering=-created_at&page_size=1")
    results = data.get("results", [])
    return results[0]["id"] if results else None


def dispatch_script_for(episode_id: str) -> None:
    code = (
        "from apps.scheduler.tasks.base import create_scheduled_job; "
        "from apps.scheduler.models import JobType; "
        f"print(create_scheduled_job(JobType.GENERATE_SCRIPT, "
        f"payload={{'episode_id': '{episode_id}', 'scheduled': True}}))"
    )
    subprocess.run(
        ["docker", "compose", "exec", "-T", "web",
         "python", "manage.py", "shell", "-c", code],
        check=True, capture_output=True, text=True, cwd=REPO,
    )


def main() -> int:
    for job_type, module, func in STAGES:
        if job_type == "generate_audio":
            # Script first: handler needs the episode id from planning.
            episode_id = newest_episode_id()
            if not episode_id:
                print("no episode to script")
                return 1
            prev = newest_job("generate_script")
            prev_id = prev["id"] if prev else None
            print(f"--- dispatching generate_script for {episode_id}")
            dispatch_script_for(episode_id)
            if not wait_stage("generate_script", prev_id):
                return 1

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
