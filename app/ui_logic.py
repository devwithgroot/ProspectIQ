from __future__ import annotations

from pathlib import Path

from app.email_verify import is_email
from app.prospect_upload import MAX_UPLOAD_BYTES, load_prospect_csv
from config.catalog import catalog_error


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


def invalid_catalog_selection(title: str, industry: str) -> str | None:
    return catalog_error(title, industry)


def upload_too_large(size_bytes: int | None) -> bool:
    if size_bytes is None:
        return False
    return size_bytes > MAX_UPLOAD_BYTES


def preview_prospect_csv(path: str | Path) -> list[dict]:
    return [row.model_dump() for row in load_prospect_csv(path)]
