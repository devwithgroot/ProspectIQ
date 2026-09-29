import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel

from app import research_jobs
from app.pipeline import ResearchCancelled, ResearchSkipped, UserPipeline
from app.prospect_upload import UploadedProspect
from app.research_jobs import (
    ResearchJobStore,
    _company_from_progress,
    percent_for,
    research_phases,
)
from app.server import app
from config.excon_schemas import Company, CompanyProfile, User


class _FakeResult(BaseModel):
    company: str = "Acme"
    companies: list = []


def main():
    print("\n==============================")
    print("RESEARCH JOB TEST")
    print("==============================")

    phases = research_phases(["Asian Paints", "Havells India"])
    assert phases[0] == "Thinking"
    assert "Searching public sources for Asian Paints" in phases
    assert "Finding people at Asian Paints" in phases
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
        assert lost.get("error_detail")
        print("refresh after server restart is lost")

        failed = ResearchJobStore(Path(folder))
        broken = failed.start(["Acme"])
        failed.fail(
            broken["job_id"],
            "We couldn’t finish research.",
            detail="TimeoutError: mlx timed out",
        )
        stored = failed.get(broken["job_id"])
        assert stored is not None
        assert stored["status"] == "error"
        assert stored["error_detail"] == "TimeoutError: mlx timed out"
        print("fail stores error_detail")

        first.complete(job["job_id"], {"ok": True})
        done = first.get(job["job_id"])
        assert done is not None
        assert done["status"] == "done"
        assert done["percent"] == 100
        print("complete keeps result for a later poll")

        third = ResearchJobStore(Path(folder))
        live = third.start(["Acme", "Beta"])
        third.progress(live["job_id"], "Looking into Acme (1/2)")
        assert third.get(live["job_id"])["current_company"] == "Acme"
        skipped = third.request_skip(live["job_id"])
        assert skipped is not None
        assert skipped["skip_requested"] is True
        assert skipped["skip_company"] == "Acme"
        assert skipped["current"] == "Skipping Acme"
        assert third.take_control(live["job_id"]) == "skip"
        assert third.take_control(live["job_id"]) == "ok"
        print("skip current company once")

        third.progress(live["job_id"], "Looking into Beta (2/2)")
        cancelled = third.request_cancel(live["job_id"])
        assert cancelled is not None
        assert cancelled["cancel_requested"] is True
        assert third.take_control(live["job_id"]) == "cancel"
        stopped = third.cancel(live["job_id"], {"companies": [{"name": "Acme"}]})
        assert stopped is not None
        assert stopped["status"] == "cancelled"
        assert stopped["result"]["companies"][0]["name"] == "Acme"
        assert third.request_cancel(live["job_id"])["status"] == "cancelled"
        print("cancel keeps finished companies")

    assert _company_from_progress(
        "Looking into Acme (1/2)", ["Acme", "Beta"], None
    ) == "Acme"
    assert _company_from_progress(
        "Writing a briefing for Priya", ["Acme"], "Acme"
    ) == "Acme"
    assert (
        _company_from_progress("Moving to the next company", ["Acme"], "Acme")
        is None
    )
    print("current company from progress ok")

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

        with patch("app.server.UserPipeline", FakePipeline):
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

        class SlowPipeline:
            def run(self, **kwargs):
                on_progress = kwargs.get("on_progress")
                for _ in range(40):
                    try:
                        if on_progress:
                            on_progress("Looking into Acme")
                            on_progress("Reading what we found on Acme")
                    except ResearchSkipped:
                        continue
                    time.sleep(0.02)
                return _FakeResult()

        with patch("app.server.UserPipeline", SlowPipeline):
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
            job_id = started.json()["job_id"]

            deadline = time.time() + 2
            status = None
            while time.time() < deadline:
                status = client.get(f"/api/research/{job_id}").json()
                if status.get("current_company"):
                    break
                time.sleep(0.02)
            assert status is not None
            assert status["current_company"] == "Acme"

            skipped = client.post(f"/api/research/{job_id}/skip")
            assert skipped.status_code == 200
            assert skipped.json()["current"] == "Skipping Acme"
            stopped = client.post(f"/api/research/{job_id}/cancel")
            assert stopped.status_code == 200
            assert stopped.json()["cancel_requested"] is True

            deadline = time.time() + 2
            status = None
            while time.time() < deadline:
                status = client.get(f"/api/research/{job_id}").json()
                if status["status"] == "cancelled":
                    break
                time.sleep(0.05)

            assert status is not None
            assert status["status"] == "cancelled"
            print("api skip + cancel ok")

        unknown = client.post("/api/research/rj_missing/cancel")
        assert unknown.status_code == 404
        print("unknown cancel 404")

    _test_pipeline_skip_and_cancel()

    research_jobs.jobs = previous
    print("\nRESEARCH JOB TEST PASSED")


def _fake_company(name: str) -> tuple[Company, CompanyProfile]:
    company = Company(
        company_id=f"co_{name.lower()}",
        name=name,
        industry="Software / SaaS",
        description=f"{name} description",
    )
    profile = CompanyProfile(
        profile_id=f"cp_{name.lower()}",
        company_id=company.company_id,
        executive_summary=f"{name} summary",
        overall_score=70,
        recommendation="potential",
        recommended_sales_approach="Call the buyer.",
        why_relevant_to_user="Fit",
    )
    return company, profile


def _test_pipeline_skip_and_cancel() -> None:
    user = User.model_validate(
        json.loads(Path("data/mock/user.json").read_text(encoding="utf-8"))
    )
    rows = [
        UploadedProspect(company_name="Acme"),
        UploadedProspect(company_name="Beta"),
    ]

    def analyze(*, company_name: str, research_goal: str, on_progress=None):
        del research_goal
        if on_progress:
            on_progress(f"Searching public sources for {company_name}")
        if company_name == "Beta":
            raise ResearchSkipped()
        return object()

    pipeline = UserPipeline()
    pipeline.onboarder.enroll = lambda **kwargs: (user, [])
    pipeline.analyzer.analyze = analyze
    pipeline._find_people = lambda *args, **kwargs: ([], [])

    with (
        patch("app.pipeline.load_prospect_csv", return_value=rows),
        patch("app.pipeline.report_to_company", side_effect=lambda **kwargs: _fake_company(kwargs["uploaded"].company_name)),
        patch("app.pipeline.save_run", return_value=Path("/tmp/run")),
    ):
        result = pipeline.run(
            full_name=user.full_name,
            phone=user.phone or "",
            email=user.email,
            website=user.company.website,
            prospects_csv="unused.csv",
            title=user.title,
            industry=user.company.industry,
        )
        assert [company.name for company in result.companies] == ["Acme"]
        print("pipeline skip drops that company")

        def cancel_second(*, company_name: str, research_goal: str, on_progress=None):
            del research_goal
            if on_progress:
                on_progress(f"Searching public sources for {company_name}")
            if company_name == "Beta":
                raise ResearchCancelled()
            return object()

        pipeline.analyzer.analyze = cancel_second
        try:
            pipeline.run(
                full_name=user.full_name,
                phone=user.phone or "",
                email=user.email,
                website=user.company.website,
                prospects_csv="unused.csv",
                title=user.title,
                industry=user.company.industry,
            )
            raise AssertionError("cancel should stop the run")
        except ResearchCancelled as exc:
            assert exc.result is not None
            assert [company.name for company in exc.result.companies] == ["Acme"]
            print("pipeline cancel keeps finished companies")


if __name__ == "__main__":
    main()
