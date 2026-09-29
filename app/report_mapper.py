from __future__ import annotations

import re

from config.excon_schemas import (
    Company,
    CompanyProfile,
    CompanySignal,
    Product,
    User,
)
from config.schemas import ProspectReport

from app.prospect_upload import UploadedProspect


def slug(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return f"{prefix}_{cleaned[:40] or 'unknown'}"


def report_to_company(
    report: ProspectReport,
    uploaded: UploadedProspect,
    user: User,
    products: list[Product],
) -> tuple[Company, CompanyProfile]:
    signals = [
        CompanySignal(
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

    company_id = slug(report.company_name, "co")
    company = Company(
        company_id=company_id,
        name=report.company_name,
        website=uploaded.website,
        industry="Unknown",
        description=report.executive_summary,
        sources=sources,
    )
    profile = CompanyProfile(
        profile_id=slug(report.company_name, "cp"),
        company_id=company_id,
        executive_summary=report.executive_summary,
        overall_score=report.prospect_score,
        recommendation=report.recommendation,
        signals=signals,
        pain_points=list(report.risks),
        risks=list(report.risks),
        recommended_sales_approach=report.recommended_sales_approach,
        why_relevant_to_user=why,
        matched_product_ids=product_ids,
    )
    return company, profile
