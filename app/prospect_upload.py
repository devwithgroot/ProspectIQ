from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel


class UploadedProspect(BaseModel):
    company_name: str
    website: str | None = None
    notes: str | None = None


REQUIRED_COLUMN = "company_name"
MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def company_domain_from_website(website: str | None) -> str | None:
    """Host-only domain for prospect company URLs (e.g. acme.com)."""
    if not website or not website.strip():
        return None

    url = website.strip()
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    host = (urlparse(url).hostname or "").lower().strip()
    if not host:
        return None

    if host.startswith("www."):
        host = host[4:]

    return host or None


def load_prospect_csv(path: str | Path) -> list[UploadedProspect]:
    csv_path = Path(path)
    if not csv_path.is_file():
        raise FileNotFoundError(f"Prospect CSV not found: {csv_path}")

    size = csv_path.stat().st_size
    if size > MAX_UPLOAD_BYTES:
        raise ValueError(
            f"File is {size / (1024 * 1024):.1f} MB. "
            "Maximum is 5 MB per file."
        )

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("Prospect CSV has no header row.")

        headers = {
            name.strip().lower(): name
            for name in reader.fieldnames
            if name and name.strip()
        }

        if REQUIRED_COLUMN not in headers:
            raise ValueError(
                "Prospect CSV must include a company_name column."
            )

        rows: list[UploadedProspect] = []
        seen: set[str] = set()

        for index, raw in enumerate(reader, start=2):
            name = (raw.get(headers[REQUIRED_COLUMN]) or "").strip()
            if not name:
                raise ValueError(f"Row {index} is missing company_name.")

            key = name.lower()
            if key in seen:
                continue
            seen.add(key)

            website = _optional(raw, headers, "website")
            notes = _optional(raw, headers, "notes")

            rows.append(
                UploadedProspect(
                    company_name=name,
                    website=website,
                    notes=notes,
                )
            )

    if not rows:
        raise ValueError("Prospect CSV does not contain any companies.")

    return rows


def _optional(
    raw: dict[str, str | None],
    headers: dict[str, str],
    column: str,
) -> str | None:
    source = headers.get(column)
    if not source:
        return None
    value = (raw.get(source) or "").strip()
    return value or None
