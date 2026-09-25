from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from threading import Thread

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.email_verify import otp_required, verifier
from app.pipeline import SellerPipeline
from app.prospect_upload import MAX_UPLOAD_BYTES, load_prospect_csv
from app import research_jobs
from app.ui_logic import (
    invalid_catalog_selection,
    invalid_email_fields,
    missing_required_fields,
    normalize_url,
    preview_prospect_csv,
    upload_too_large,
)
from config.catalog import catalog_payload


app = FastAPI(title="ProspectIQ API")
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/catalog")
def catalog() -> dict:
    return catalog_payload()


@app.get("/api/settings")
def settings() -> dict[str, bool]:
    return {"otp_required": otp_required()}


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

    catalog_problem = invalid_catalog_selection(title=title, industry=industry)
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


@app.get("/api/research/{job_id}")
def research_status(job_id: str) -> dict:
    job = research_jobs.jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="That research run was not found.")
    return job


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
) -> None:
    def on_progress(message: str) -> None:
        research_jobs.jobs.progress(job_id, message)

    try:
        result = SellerPipeline().run(
            full_name=full_name,
            phone=phone,
            email=email,
            outreach_email=outreach_email,
            outreach_email_verified=verifier.is_verified(outreach_email),
            website=website,
            prospects_csv=prospects_csv,
            title=title,
            industry=industry,
            on_progress=on_progress,
        )
        research_jobs.jobs.complete(job_id, result.model_dump(mode="json"))
    except ValueError as exc:
        research_jobs.jobs.fail(job_id, str(exc))
    except Exception:
        logging.exception("Research job %s failed", job_id)
        research_jobs.jobs.fail(
            job_id,
            "We couldn’t finish research. Start it again from your list.",
        )
    finally:
        prospects_csv.unlink(missing_ok=True)
