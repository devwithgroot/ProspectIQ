from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Literal
from uuid import uuid4


JOBS_DIR = Path(__file__).resolve().parent.parent / "data" / "jobs"

JobStatus = Literal["running", "done", "error", "lost"]


def research_phases(company_names: list[str]) -> list[str]:
    names = [name.strip() for name in company_names if name.strip()]
    names = names or ["this company"]
    phases = [
        "Thinking",
        "Reading your company website",
        "Learning what you sell",
    ]
    for name in names:
        phases.append(f"Searching public sources for {name}")
        phases.append(f"Reading what we found on {name}")
        phases.append(f"Writing the briefing for {name}")
    phases.append("Putting the briefings together")
    return phases


def percent_for(
    companies: list[str],
    current: str,
    done: list[str] | None = None,
) -> int:
    if current == "Putting the briefings together":
        return 92
    count = max(len([name for name in companies if str(name).strip()]), 1)
    expected = max(8, 6 + 10 * count)
    completed = len(done or []) + 1
    return min(92, max(1, round((completed / expected) * 92)))


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResearchJobStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or JOBS_DIR
        self.directory.mkdir(parents=True, exist_ok=True)
        self._live: dict[str, dict[str, Any]] = {}
        self._lock = Lock()

    def start(self, companies: list[str]) -> dict[str, Any]:
        job_id = f"rj_{uuid4().hex[:12]}"
        job: dict[str, Any] = {
            "job_id": job_id,
            "status": "running",
            "started_at": _utc_now(),
            "updated_at": _utc_now(),
            "companies": list(companies),
            "current": "Opening your website",
            "done": [],
            "percent": 0,
            "result": None,
            "error": None,
        }
        with self._lock:
            self._live[job_id] = job
            self._write(job)
            return deepcopy(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            if job_id in self._live:
                return deepcopy(self._live[job_id])

            disk = self._read(job_id)
            if disk is None:
                return None

            if disk.get("status") == "running":
                disk["status"] = "lost"
                disk["error"] = (
                    "Research stopped because the server restarted. "
                    "Start it again from your list."
                )
                disk["updated_at"] = _utc_now()
                self._write(disk)
            return disk

    def progress(self, job_id: str, message: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._live.get(job_id)
            if job is None or job["status"] != "running":
                return None
            current = str(job.get("current") or "")
            if current and current != message and current not in job["done"]:
                job["done"].append(current)
            job["current"] = message
            job["percent"] = percent_for(job["companies"], message, job["done"])
            job["updated_at"] = _utc_now()
            self._write(job)
            return deepcopy(job)

    def complete(self, job_id: str, result: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock:
            job = self._live.get(job_id)
            if job is None:
                return None
            current = str(job.get("current") or "")
            if current and current not in job["done"]:
                job["done"].append(current)
            job["status"] = "done"
            job["current"] = "Putting the briefings together"
            job["percent"] = 100
            job["result"] = result
            job["error"] = None
            job["updated_at"] = _utc_now()
            self._write(job)
            return deepcopy(job)

    def fail(self, job_id: str, error: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._live.get(job_id)
            if job is None:
                return None
            job["status"] = "error"
            job["error"] = error
            job["updated_at"] = _utc_now()
            self._write(job)
            return deepcopy(job)

    def _path(self, job_id: str) -> Path:
        return self.directory / f"{job_id}.json"

    def _write(self, job: dict[str, Any]) -> None:
        path = self._path(job["job_id"])
        path.write_text(json.dumps(job, indent=2), encoding="utf-8")

    def _read(self, job_id: str) -> dict[str, Any] | None:
        path = self._path(job_id)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))


jobs = ResearchJobStore()
