import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import research_jobs
from app.research_jobs import ResearchJobStore, percent_for, research_phases
from app.server import app


class _FakeResult(BaseModel):
    company: str = "Acme"


def main():
    print("\n==============================")
    print("RESEARCH JOB TEST")
    print("==============================")

    phases = research_phases(["Asian Paints", "Havells India"])
    assert phases[0] == "Thinking"
    assert "Searching public sources for Asian Paints" in phases
    assert phases[-1] == "Putting the briefings together"
    assert percent_for(["Asian Paints"], "Thinking") >= 1
    assert (
        percent_for(["Asian Paints"], "Searching", ["a", "b", "c"])
        > percent_for(["Asian Paints"], "Thinking")
    )
    assert percent_for(["Asian Paints"], "Putting the briefings together") == 92
    print("phase percents ok")

    with tempfile.TemporaryDirectory() as folder:
        first = ResearchJobStore(Path(folder))
        job = first.start(["Acme"])
        assert job["status"] == "running"
        first.progress(job["job_id"], "Reading your company website")
        first.progress(job["job_id"], "Searching public sources for Acme")
        live = first.get(job["job_id"])
        assert live is not None
        assert live["current"] == "Searching public sources for Acme"
        assert "Reading your company website" in live["done"]

        second = ResearchJobStore(Path(folder))
        lost = second.get(job["job_id"])
        assert lost is not None
        assert lost["status"] == "lost"
        print("refresh after server restart is lost")

        first.complete(job["job_id"], {"ok": True})
        done = first.get(job["job_id"])
        assert done is not None
        assert done["status"] == "done"
        assert done["percent"] == 100
        print("complete keeps result for a later poll")

    previous = research_jobs.jobs
    with tempfile.TemporaryDirectory() as folder:
        research_jobs.jobs = ResearchJobStore(Path(folder))
        client = TestClient(app)

        class FakePipeline:
            def run(self, **kwargs):
                on_progress = kwargs.get("on_progress")
                if on_progress:
                    on_progress("Reading your company website")
                    on_progress("Searching public sources for Acme")
                time.sleep(0.05)
                return _FakeResult()

        with patch("app.server.SellerPipeline", FakePipeline):
            started = client.post(
                "/api/research",
                data={
                    "full_name": "Priya Mehta",
                    "phone": "+919845512210",
                    "email": "priya@nexusflow.io",
                    "outreach_email": "priya.sales@nexusflow.io",
                    "website": "https://www.zoho.com",
                    "title": "Account Executive",
                    "industry": "Software / SaaS",
                },
                files={
                    "prospects": (
                        "prospects.csv",
                        b"company_name\nAcme\n",
                        "text/csv",
                    )
                },
            )
            assert started.status_code == 200
            body = started.json()
            assert body["status"] == "running"
            job_id = body["job_id"]

            deadline = time.time() + 2
            status = None
            while time.time() < deadline:
                status = client.get(f"/api/research/{job_id}").json()
                if status["status"] == "done":
                    break
                time.sleep(0.05)

            assert status is not None
            assert status["status"] == "done"
            assert status["result"]["company"] == "Acme"
            print("api start + poll ok")

        missing = client.get("/api/research/rj_missing")
        assert missing.status_code == 404
        print("unknown job 404")

    research_jobs.jobs = previous
    print("\nRESEARCH JOB TEST PASSED")


if __name__ == "__main__":
    main()
