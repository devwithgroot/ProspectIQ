from __future__ import annotations

import re

from config.excon_schemas import Product, Prospect, ProspectSignal, User
from config.schemas import ProspectReport

from app.prospect_upload import UploadedProspect


def slug(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return f"{prefix}_{cleaned[:40] or 'unknown'}"


def report_to_prospect(
    report: ProspectReport,
    uploaded: UploadedProspect,
    user: User,
    products: list[Product],
) -> Prospect:
    signals = [
        ProspectSignal(
            type="research",
            description=signal,
            strength="medium",
        )
        for signal in report.key_signals
    ]

    sources = [
        evidence.url
        for evidence in report.evidence
        if evidence.url
    ]

    product_ids = [product.product_id for product in products]
    why = uploaded.notes or report.recommended_sales_approach
    if user.company.name:
        why = (
            f"{why} Relevant to {user.company.name} "
            f"based on the uploaded list and research."
        )

    return Prospect(
        prospect_id=slug(report.company_name, "pr"),
        company_name=report.company_name,
        website=uploaded.website,
        industry="Unknown",
        description=report.executive_summary,
        signals=signals,
        pain_points=list(report.risks),
        overall_score=report.prospect_score,
        recommendation=report.recommendation,
        why_relevant_to_user=why,
        matched_product_ids=product_ids,
        sources=sources,
    )
