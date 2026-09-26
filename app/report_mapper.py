from __future__ import annotations

import re

from config.excon_schemas import (
    Company,
    CompanyProfile,
    CompanySignal,
    Product,
    User,
)
from config.schemas import Evidence, ProspectReport

from app.prospect_upload import UploadedProspect

EVIDENCE_CONTENT_LIMIT = 700

_TOKEN_RE = re.compile(r"\b[a-z0-9]{4,}\b")

_STOPWORDS = frozenset(
    {
        "about",
        "also",
        "been",
        "being",
        "both",
        "from",
        "have",
        "into",
        "more",
        "only",
        "such",
        "than",
        "that",
        "their",
        "them",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "very",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "with",
        "would",
        "your",
    }
)


def slug(value: str, prefix: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return f"{prefix}_{cleaned[:40] or 'unknown'}"


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(
        match.group(0)
        for match in _TOKEN_RE.finditer(text.lower())
        if match.group(0) not in _STOPWORDS
    )


def _meaningful_overlap_size(
    signal: str,
    evidence: Evidence,
    company_name: str,
) -> int:
    claim_tokens = _tokenize(signal)
    if not claim_tokens:
        return 0

    evidence_text = f"{evidence.title} {evidence.content[:EVIDENCE_CONTENT_LIMIT]}"
    evidence_tokens = _tokenize(evidence_text)
    company_tokens = _tokenize(company_name)
    return len((claim_tokens & evidence_tokens) - company_tokens)


def _signal_qualifies_for_evidence(
    signal: str,
    evidence: Evidence,
    company_name: str,
) -> bool:
    claim_tokens = _tokenize(signal)
    if not claim_tokens:
        return False

    overlap_size = _meaningful_overlap_size(signal, evidence, company_name)
    min_overlap = 1 if len(claim_tokens) <= 6 else 2
    return overlap_size >= min_overlap


def _best_evidence_for_signal(
    signal: str,
    evidence_items: list[Evidence],
    company_name: str,
) -> Evidence | None:
    best: Evidence | None = None
    best_overlap = -1
    best_index = -1

    for index, item in enumerate(evidence_items):
        if not _signal_qualifies_for_evidence(signal, item, company_name):
            continue

        overlap_size = _meaningful_overlap_size(signal, item, company_name)
        if best is None:
            best, best_overlap, best_index = item, overlap_size, index
            continue

        if overlap_size > best_overlap:
            best, best_overlap, best_index = item, overlap_size, index
            continue
        if overlap_size < best_overlap:
            continue

        if item.relevance > best.relevance:
            best, best_overlap, best_index = item, overlap_size, index
            continue
        if item.relevance < best.relevance:
            continue

        if item.quality > best.quality:
            best, best_overlap, best_index = item, overlap_size, index
            continue
        if item.quality < best.quality:
            continue

        if index < best_index:
            best, best_overlap, best_index = item, overlap_size, index

    return best


def _signal_evidence_citation(
    signal: str,
    evidence_items: list[Evidence],
    company_name: str,
) -> str | None:
    best = _best_evidence_for_signal(signal, evidence_items, company_name)
    if best is None or not best.url:
        return None
    return f"{best.title} — {best.url}"


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
            evidence=_signal_evidence_citation(
                signal,
                report.evidence,
                report.company_name,
            ),
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
