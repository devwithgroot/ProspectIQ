from __future__ import annotations

import json
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.email_verify import is_email, otp_required, verifier
from app.outreach import draft_for_contact
from app.pipeline import ResearchCancelled, ResearchSkipped, UserPipeline
from config.excon_schemas import Product, User
from app.prospect_upload import load_prospect_csv, preview_prospect_csv, upload_too_large
from app import research_jobs
from config.catalog import catalog_error, catalog_payload
from config.research_log import configure_logging, get_logger, quiet_access_logs
from data.loader import load_mock_bundle

configure_logging()
log = get_logger("api")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    quiet_access_logs()
    log.info("API ready — research logs print in this terminal")
    yield


app = FastAPI(title="ProspectIQ API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class VerifyStart(BaseModel):
    email: str


class VerifyConfirm(BaseModel):
    email: str
    code: str


class OutreachDraftRequest(BaseModel):
    contact_id: str
    job_id: str | None = None
    result: dict | None = None
    channel: str | None = None


def normalize_url(url: str) -> str:
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def missing_required_fields(
    *,
    full_name: str,
    phone: str,
    email: str,
    outreach_email: str,
    website: str,
    title: str,
    industry: str,
    has_csv: bool,
) -> list[str]:
    missing = [
        label
        for label, value in (
            ("Full name", full_name),
            ("Phone", phone),
            ("Email", email),
            ("Outreach email", outreach_email),
            ("Industry", industry),
            ("Title", title),
            ("Company website", website),
        )
        if not value.strip()
    ]
    if not has_csv:
        missing.append("Prospect CSV")
    return missing


def invalid_email_fields(email: str, outreach_email: str) -> str | None:
    if email.strip() and not is_email(email):
        return "Please enter a valid work email."
    if outreach_email.strip() and not is_email(outreach_email):
        return "Please enter a valid outreach email."
    return None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/catalog")
def catalog() -> dict:
    return catalog_payload()


@app.get("/api/settings")
def settings() -> dict[str, bool]:
    return {"otp_required": otp_required()}


@app.get("/api/mock/bundle")
def mock_bundle() -> dict:
    bundle = load_mock_bundle()
    return {
        "user": bundle.user.model_dump(mode="json"),
        "products": [item.model_dump(mode="json") for item in bundle.products],
        "companies": [item.model_dump(mode="json") for item in bundle.companies],
        "company_profiles": [
            item.model_dump(mode="json") for item in bundle.company_profiles
        ],
        "contacts": [item.model_dump(mode="json") for item in bundle.contacts],
        "contact_profiles": [
            item.model_dump(mode="json") for item in bundle.contact_profiles
        ],
        "do_not_contact": [item.model_dump(mode="json") for item in bundle.dnc],
    }


@app.post("/api/verify-email")
def verify_email_start(payload: VerifyStart) -> dict:
    try:
        return verifier.start(payload.email)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/verify-email/confirm")
def verify_email_confirm(payload: VerifyConfirm) -> dict[str, bool]:
    try:
        verifier.confirm(payload.email, payload.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"verified": True}


@app.post("/api/preview")
async def preview(prospects: UploadFile = File(...)) -> dict:
    filename = prospects.filename or "prospects.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    payload = await prospects.read()
    if upload_too_large(len(payload)):
        raise HTTPException(
            status_code=400,
            detail="Maximum is 5 MB per file.",
        )

    handle = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    path = Path(handle.name)
    try:
        handle.write(payload)
        handle.close()
        companies = preview_prospect_csv(path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        path.unlink(missing_ok=True)

    return {
        "file_name": filename,
        "count": len(companies),
        "companies": companies,
    }


@app.post("/api/research")
async def research(
    full_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    outreach_email: str = Form(""),
    website: str = Form(...),
    title: str = Form(...),
    industry: str = Form(...),
    prospects: UploadFile = File(...),
    seller: str = Form(""),
):
    website = normalize_url(website)
    outreach = (outreach_email or email).strip()
    missing = missing_required_fields(
        full_name=full_name,
        phone=phone,
        email=email,
        outreach_email=outreach,
        website=website,
        title=title,
        industry=industry,
        has_csv=prospects.filename is not None,
    )
    if missing:
        raise HTTPException(
            status_code=400,
            detail="Required: " + ", ".join(missing),
        )

    email_problem = invalid_email_fields(email, outreach)
    if email_problem:
        raise HTTPException(status_code=400, detail=email_problem)

    catalog_problem = catalog_error(title=title, industry=industry)
    if catalog_problem:
        raise HTTPException(status_code=400, detail=catalog_problem)

    filename = prospects.filename or "prospects.csv"
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a CSV file.")

    payload = await prospects.read()
    if upload_too_large(len(payload)):
        raise HTTPException(
            status_code=400,
            detail="Maximum is 5 MB per file.",
        )

    handle = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    csv_path = Path(handle.name)
    try:
        handle.write(payload)
        handle.close()
        staged = load_prospect_csv(csv_path)
    except ValueError as exc:
        csv_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    companies = [row.company_name for row in staged]
    job = research_jobs.jobs.start(companies)
    log.info(
        "Research job %s started seller=%s website=%s companies=%s",
        job["job_id"],
        email.strip(),
        website,
        companies,
    )
    job_csv = research_jobs.jobs.directory / f"{job['job_id']}.csv"
    job_csv.write_bytes(payload)
    csv_path.unlink(missing_ok=True)

    thread = Thread(
        target=_run_research_job,
        kwargs={
            "job_id": job["job_id"],
            "full_name": full_name.strip(),
            "phone": phone.strip(),
            "email": email.strip(),
            "outreach_email": outreach,
            "website": website,
            "title": title.strip(),
            "industry": industry.strip(),
            "prospects_csv": job_csv,
            "seller_json": seller,
        },
        daemon=True,
    )
    thread.start()
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "started_at": job["started_at"],
        "companies": job["companies"],
    }


@app.post("/api/outreach/draft")
def outreach_draft(payload: OutreachDraftRequest) -> dict:
    result = payload.result
    if payload.job_id:
        job = research_jobs.jobs.get(payload.job_id)
        if job is None:
            raise HTTPException(
                status_code=404,
                detail="That research run was not found.",
            )
        if job.get("result"):
            result = job["result"]
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Research results are required to write a draft.",
        )
    try:
        return draft_for_contact(result, payload.contact_id, payload.channel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/research/{job_id}")
def research_status(job_id: str) -> dict:
    job = research_jobs.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="That research run was not found.")
    return job


@app.post("/api/research/{job_id}/cancel")
def cancel_research(job_id: str) -> dict:
    job = research_jobs.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="That research run was not found.")
    if job.get("status") != "running":
        return job
    updated = research_jobs.jobs.request_cancel(job_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="That research run was not found.")
    return updated


@app.post("/api/research/{job_id}/skip")
def skip_research_company(job_id: str) -> dict:
    job = research_jobs.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="That research run was not found.")
    if job.get("status") != "running":
        return job
    if not job.get("current_company"):
        return job
    updated = research_jobs.jobs.request_skip(job_id)
    if updated is None:
        raise HTTPException(status_code=404, detail="That research run was not found.")
    return updated


def _run_research_job(
    *,
    job_id: str,
    full_name: str,
    phone: str,
    email: str,
    outreach_email: str,
    website: str,
    title: str,
    industry: str,
    prospects_csv: Path,
    seller_json: str = "",
) -> None:
    def on_progress(message: str) -> None:
        research_jobs.jobs.progress(job_id, message)
        action = research_jobs.jobs.take_control(job_id)
        if action == "cancel":
            raise ResearchCancelled()
        if action == "skip":
            raise ResearchSkipped()

    saved_user, saved_products = _saved_seller(seller_json)
    log.info("Research job %s running", job_id)
    try:
        result = UserPipeline().run(
            full_name=full_name,
            phone=phone,
            email=email,
            outreach_email=outreach_email,
            outreach_email_verified=verifier.is_verified(outreach_email),
            website=website,
            prospects_csv=prospects_csv,
            title=title,
            industry=industry,
            saved_user=saved_user,
            saved_products=saved_products,
            on_progress=on_progress,
        )
        research_jobs.jobs.complete(job_id, result.model_dump(mode="json"))
        log.info("Research job %s complete companies=%s", job_id, len(result.companies))
    except ResearchCancelled as exc:
        payload = (
            exc.result.model_dump(mode="json") if exc.result is not None else None
        )
        research_jobs.jobs.cancel(job_id, payload)
        log.info("Research job %s cancelled", job_id)
    except ValueError as exc:
        log.exception("Research job %s rejected: %s", job_id, exc)
        research_jobs.jobs.fail(
            job_id,
            str(exc),
            detail=f"{type(exc).__name__}: {exc}",
        )
    except Exception as exc:
        log.exception("Research job %s failed", job_id)
        research_jobs.jobs.fail(
            job_id,
            "We couldn’t finish research. Start it again from your list.",
            detail=f"{type(exc).__name__}: {exc}",
        )
    finally:
        prospects_csv.unlink(missing_ok=True)


def _saved_seller(raw: str) -> tuple[User | None, list[Product]]:
    text = (raw or "").strip()
    if not text:
        return None, []
    try:
        payload = json.loads(text)
        user = User.model_validate(payload["user"])
        products = [
            Product.model_validate(item)
            for item in payload.get("products") or []
        ]
    except Exception:
        return None, []
    if not products:
        return None, []
    return user, products
