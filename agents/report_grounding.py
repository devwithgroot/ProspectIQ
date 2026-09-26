from __future__ import annotations

import re

from agents.state import ResearchState
from config.schemas import ProspectReport, ProspectScore

EVIDENCE_CONTENT_LIMIT = 700

EXECUTIVE_SUMMARY_CAVEAT = (
    "Some statements above could not be matched to collected snippets; "
    "rely on sources and scores."
)

_TOKEN_RE = re.compile(r"\b[a-z0-9]{4,}\b")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

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

_SCORE_ONLY_WORDS = frozenset(
    {
        "assessment",
        "confidence",
        "dimension",
        "dimensions",
        "expansion",
        "growth",
        "hiring",
        "overall",
        "potential",
        "priority",
        "prospect",
        "rated",
        "recommendation",
        "score",
        "scores",
        "strategic",
        "technology",
        "valuable",
    }
)

_META_RISK_PHRASES = (
    "limited evidence",
    "insufficient",
    "unclear",
    "unknown",
    "missing",
    "not available",
    "uncertainty",
    "low confidence",
    "thin research",
    "could not verify",
    "couldn't verify",
    "not found",
    "unverified",
    "gap in",
    "gaps in",
    "lack of evidence",
    "no evidence",
    "insufficient data",
    "limited public",
    "limited research",
)

_SIGNAL_LEXICON: tuple[str, ...] = (
    "growth",
    "revenue",
    "demand",
    "scale",
    "expansion",
    "expand",
    "capacity",
    "geography",
    "market",
    "hiring",
    "workforce",
    "headcount",
    "recruit",
    "jobs",
    "technology",
    "digital",
    "cloud",
    "software",
    "modernization",
    "transform",
    "transformation",
    "cyber",
    "strategic",
    "acquisition",
    "merger",
    "partnership",
    "investment",
    "funding",
    "initiative",
)

_TERM_PATTERNS: dict[str, re.Pattern[str]] = {
    term: re.compile(rf"\b{re.escape(term)}\b")
    for term in _SIGNAL_LEXICON
}


def sanitize_report_narrative(
    state: ResearchState,
    score: ProspectScore,
    report: ProspectReport,
) -> None:
    corpus_text, corpus_tokens = build_grounding_corpus(state)

    company_name = state.company_name

    report.key_signals = _sanitize_key_signals(
        report.key_signals,
        corpus_text,
        corpus_tokens,
        score,
        state,
        company_name,
    )
    report.risks = _sanitize_risks(
        report.risks,
        corpus_text,
        corpus_tokens,
        state,
        company_name,
    )
    report.recommended_sales_approach = _sanitize_sales_approach(
        report.recommended_sales_approach,
        corpus_text,
        corpus_tokens,
        score,
        company_name,
    )
    report.executive_summary = _sanitize_executive_summary(
        report.executive_summary,
        corpus_text,
        corpus_tokens,
        score,
        company_name,
    )


def build_grounding_corpus(
    state: ResearchState,
) -> tuple[str, frozenset[str]]:
    parts = [state.company_name]
    for evidence in state.evidence:
        parts.extend(
            [
                evidence.title,
                evidence.url,
                evidence.content[:EVIDENCE_CONTENT_LIMIT],
            ]
        )
    corpus_text = " ".join(part for part in parts if part).lower()
    return corpus_text, _tokenize(corpus_text)


def is_grounded_positive_claim(
    text: str,
    corpus_text: str,
    corpus_tokens: frozenset[str],
    *,
    company_name: str = "",
) -> bool:
    cleaned = " ".join(text.split())
    if not cleaned:
        return False

    claim_tokens = _tokenize(cleaned.lower())
    company_tokens = _tokenize(company_name.lower())
    overlap = (claim_tokens & corpus_tokens) - company_tokens
    min_overlap = 1 if len(claim_tokens) <= 6 else 2
    if len(overlap) >= min_overlap:
        return True

    lowered = cleaned.lower()
    for term in _SIGNAL_LEXICON:
        if _TERM_PATTERNS[term].search(lowered) and _TERM_PATTERNS[term].search(
            corpus_text
        ):
            return True
    return False


def is_meta_risk(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in _META_RISK_PHRASES)


def is_score_only_sentence(
    sentence: str,
    score: ProspectScore,
    company_name: str,
) -> bool:
    lowered = sentence.lower()
    for fragment in (
        company_name,
        score.recommendation,
        f"{score.overall_score:.1f}",
        f"{score.overall_score:.0f}",
        f"{score.confidence:.2f}",
    ):
        if fragment:
            lowered = lowered.replace(fragment.lower(), " ")

    for label, value in (
        ("growth", score.growth_score),
        ("expansion", score.expansion_score),
        ("hiring", score.hiring_score),
        ("technology", score.technology_score),
        ("strategic", score.strategic_score),
    ):
        lowered = lowered.replace(f"{label} {value:.1f}", " ")
        lowered = lowered.replace(f"{label} {value:.0f}", " ")

    remaining = _tokenize(lowered)
    factual = remaining - _SCORE_ONLY_WORDS
    return len(factual) == 0


def _tokenize(text: str) -> frozenset[str]:
    return frozenset(
        match.group(0)
        for match in _TOKEN_RE.finditer(text.lower())
        if match.group(0) not in _STOPWORDS
    )


def _split_sentences(text: str) -> list[str]:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return []
    parts = [part.strip() for part in _SENTENCE_RE.split(cleaned) if part.strip()]
    return parts or [cleaned]


def _sanitize_key_signals(
    items: list[str],
    corpus_text: str,
    corpus_tokens: frozenset[str],
    score: ProspectScore,
    state: ResearchState,
    company_name: str,
) -> list[str]:
    kept = [
        item
        for item in items
        if is_grounded_positive_claim(
            item,
            corpus_text,
            corpus_tokens,
            company_name=company_name,
        )
    ]
    if kept:
        return kept
    return [_key_signals_fallback(score, state)]


def _key_signals_fallback(score: ProspectScore, state: ResearchState) -> str:
    return (
        "No specific buying signals could be matched to collected snippets; "
        f"review dimension scores (growth {score.growth_score:.0f}, "
        f"expansion {score.expansion_score:.0f}, "
        f"hiring {score.hiring_score:.0f}, "
        f"technology {score.technology_score:.0f}, "
        f"strategic {score.strategic_score:.0f}) and "
        f"{state.useful_evidence_count} useful evidence item(s)."
    )


def _sanitize_risks(
    items: list[str],
    corpus_text: str,
    corpus_tokens: frozenset[str],
    state: ResearchState,
    company_name: str,
) -> list[str]:
    kept: list[str] = []
    for item in items:
        if is_meta_risk(item):
            kept.append(item)
        elif is_grounded_positive_claim(
            item,
            corpus_text,
            corpus_tokens,
            company_name=company_name,
        ):
            kept.append(item)
    if kept:
        return kept
    return [_risks_fallback(state)]


def _risks_fallback(state: ResearchState) -> str:
    stop = state.stop_reason or "n/a"
    return (
        f"Limited research evidence ({state.useful_evidence_count} useful "
        f"snippet(s), stop reason: {stop}); validate claims manually before "
        "outreach."
    )


def _sanitize_sales_approach(
    text: str,
    corpus_text: str,
    corpus_tokens: frozenset[str],
    score: ProspectScore,
    company_name: str,
) -> str:
    sentences = _split_sentences(text)
    kept = [
        sentence
        for sentence in sentences
        if is_grounded_positive_claim(
            sentence,
            corpus_text,
            corpus_tokens,
            company_name=company_name,
        )
    ]
    if kept:
        return " ".join(kept)
    return _approach_fallback(score)


def _approach_fallback(score: ProspectScore) -> str:
    return (
        f"Treat as {score.recommendation} (overall {score.overall_score:.1f}). "
        "Use listed source URLs only and confirm fit before outreach."
    )


def _sanitize_executive_summary(
    text: str,
    corpus_text: str,
    corpus_tokens: frozenset[str],
    score: ProspectScore,
    company_name: str,
) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return text

    unsupported = False
    for sentence in sentences:
        if is_score_only_sentence(sentence, score, company_name):
            continue
        if is_meta_risk(sentence):
            continue
        if not is_grounded_positive_claim(
            sentence,
            corpus_text,
            corpus_tokens,
            company_name=company_name,
        ):
            unsupported = True
            break

    if unsupported and EXECUTIVE_SUMMARY_CAVEAT not in text:
        return f"{text.rstrip()} {EXECUTIVE_SUMMARY_CAVEAT}"
    return text
