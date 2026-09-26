import re
from collections.abc import Callable

from agents.state import ResearchState
from agents.research_prompt import research_summary_block
from config.schemas import Evidence, ProspectScore, ScoringAssessment
from llm.client import LLMClient
from llm.json_util import generate_model, reason_lines

INSUFFICIENT_EVIDENCE_CONFIDENCE_CAP = 0.35
UNSUPPORTED_DIMENSION_SCORE_CAP = 15.0

_DIMENSION_NAMES = (
    "Growth",
    "Expansion",
    "Hiring",
    "Technology",
    "Strategic",
)

_DIMENSION_LEXICONS: dict[str, tuple[str, ...]] = {
    "Growth": ("growth", "revenue", "demand", "scale"),
    "Expansion": ("expansion", "expand", "capacity", "geography", "market"),
    "Hiring": ("hiring", "workforce", "headcount", "recruit", "jobs"),
    "Technology": (
        "technology",
        "digital",
        "cloud",
        "software",
        "modernization",
        "transform",
        "transformation",
        "cyber",
    ),
    "Strategic": (
        "strategic",
        "acquisition",
        "merger",
        "partnership",
        "investment",
        "funding",
        "initiative",
    ),
}

_TERM_PATTERNS: dict[str, re.Pattern[str]] = {
    term: re.compile(rf"\b{re.escape(term)}\b")
    for terms in _DIMENSION_LEXICONS.values()
    for term in terms
}


class ScoringAgent:
    GROWTH_WEIGHT = 0.20
    EXPANSION_WEIGHT = 0.25
    HIRING_WEIGHT = 0.15
    TECHNOLOGY_WEIGHT = 0.20
    STRATEGIC_WEIGHT = 0.20

    def __init__(self):
        self.llm = LLMClient()

    def score(
        self,
        state: ResearchState,
        on_progress: Callable[[str], None] | None = None,
    ) -> ProspectScore:
        if on_progress is not None:
            on_progress(
                f"Rating how well {state.company_name} fits"
            )

        evidence_summary = self._format_evidence_summary(state)

        prompt = self._build_prompt(
            state=state,
            evidence_summary=evidence_summary,
        )

        assessment = generate_model(
            self.llm,
            ScoringAssessment,
            prompt,
            temperature=0.0,
            max_tokens=600,
        )

        confidence = self._validated_confidence(state, assessment.confidence)

        (
            growth_score,
            expansion_score,
            hiring_score,
            technology_score,
            strategic_score,
        ) = self._guarded_dimension_scores(state, assessment)

        overall_score = (
            growth_score * self.GROWTH_WEIGHT
            + expansion_score * self.EXPANSION_WEIGHT
            + hiring_score * self.HIRING_WEIGHT
            + technology_score * self.TECHNOLOGY_WEIGHT
            + strategic_score * self.STRATEGIC_WEIGHT
        )

        recommendation = self._get_recommendation(
            overall_score
        )

        if on_progress is not None:
            on_progress(
                f"{state.company_name}: {overall_score:.0f} · {recommendation}"
            )
            on_progress(
                "Why: "
                f"growth {growth_score:.0f}, "
                f"expansion {expansion_score:.0f}, "
                f"hiring {hiring_score:.0f}, "
                f"tech {technology_score:.0f}, "
                f"strategy {strategic_score:.0f}"
            )
            for line in reason_lines(" ".join(assessment.reasons), limit=3):
                on_progress(line)

        return ProspectScore(
            company_name=assessment.company_name,
            overall_score=overall_score,
            growth_score=growth_score,
            expansion_score=expansion_score,
            hiring_score=hiring_score,
            technology_score=technology_score,
            strategic_score=strategic_score,
            confidence=confidence,
            recommendation=recommendation,
            reasons=assessment.reasons,
        )

    def _format_evidence_summary(self, state: ResearchState) -> str:
        blocks = []
        for index, evidence in enumerate(state.evidence, start=1):
            supports = self._dimension_support_for_evidence(evidence)
            support_label = ", ".join(supports) if supports else "none"
            blocks.append(
                (
                    f"Evidence {index} — Supports (heuristic): {support_label}\n"
                    f"- Title: {evidence.title}\n"
                    f"  URL: {evidence.url}\n"
                    f"  Relevance: {evidence.relevance:.2f}\n"
                    f"  Quality: {evidence.quality:.2f}\n"
                    f"  Content: {evidence.content[:700]}"
                )
            )
        return "\n\n".join(blocks)

    def _dimension_support_for_evidence(self, evidence: Evidence) -> list[str]:
        combined = f"{evidence.title} {evidence.content}".lower()
        supported: list[str] = []
        for dimension in _DIMENSION_NAMES:
            if self._dimension_supported_in_text(dimension, combined):
                supported.append(dimension)
        return supported

    def _dimension_supported_in_text(self, dimension: str, text: str) -> bool:
        for term in _DIMENSION_LEXICONS[dimension]:
            if _TERM_PATTERNS[term].search(text):
                return True
        return False

    def _union_supported_dimensions(self, state: ResearchState) -> set[str]:
        supported: set[str] = set()
        for evidence in state.evidence:
            supported.update(self._dimension_support_for_evidence(evidence))
        return supported

    def _apply_unsupported_dimension_caps(
        self,
        scores: tuple[float, float, float, float, float],
        supported: set[str],
    ) -> tuple[float, float, float, float, float]:
        capped: list[float] = []
        for dimension, value in zip(_DIMENSION_NAMES, scores):
            if dimension not in supported:
                capped.append(min(value, UNSUPPORTED_DIMENSION_SCORE_CAP))
            else:
                capped.append(value)
        return tuple(capped)

    def _guarded_dimension_scores(
        self,
        state: ResearchState,
        assessment: ScoringAssessment,
    ) -> tuple[float, float, float, float, float]:
        if len(state.evidence) == 0 or state.useful_evidence_count == 0:
            return (0.0, 0.0, 0.0, 0.0, 0.0)
        scores = (
            assessment.growth_score,
            assessment.expansion_score,
            assessment.hiring_score,
            assessment.technology_score,
            assessment.strategic_score,
        )
        supported = self._union_supported_dimensions(state)
        return self._apply_unsupported_dimension_caps(scores, supported)

    def _validated_confidence(
        self,
        state: ResearchState,
        confidence: float,
    ) -> float:
        if len(state.evidence) == 0 or state.useful_evidence_count == 0:
            return min(confidence, INSUFFICIENT_EVIDENCE_CONFIDENCE_CAP)
        return confidence

    def _build_prompt(
        self,
        *,
        state: ResearchState,
        evidence_summary: str,
    ) -> str:
        summary = research_summary_block(state)

        return f"""
You are the ProspectIQ sales intelligence scoring agent.

Evaluate this company as a potential high-value B2B
sales prospect using ONLY the evidence below.

Company:
{state.company_name}

Research goal:
{state.research_goal}
{summary}
Evidence:
{evidence_summary}

Score these five dimensions from 0 to 100:

1. growth_score
2. expansion_score
3. hiring_score
4. technology_score
5. strategic_score

Dimension definitions:

Growth — strength of growth signals (revenue, demand, scale).

Expansion — expansion, capacity, geography, or market-entry signals.

Hiring — hiring and workforce-growth signals.

Technology — technology investment, digital transformation,
or technology-related workforce signals.

Strategic — acquisitions, strategic initiatives, investments,
partnerships, or major business changes.

Score rubric (apply per dimension):

- 0–20: no meaningful evidence
- 21–40: weak evidence
- 41–60: moderate evidence
- 61–80: strong evidence
- 81–100: very strong / multiple corroborating signals

Scoring rules:

- Use ONLY the available evidence above. Do not invent facts
  or evidence to fill gaps.
- Score each dimension only from evidence that supports that
  dimension.
- Score a dimension above 15 only when at least one evidence
  item lists that dimension under Supports (heuristic).
- If there is no evidence for a dimension, score that dimension
  conservatively (15 or below).
- Do not use the same fact as strong evidence for multiple
  dimensions unless the evidence genuinely supports each
  dimension.
- Do not infer typical industry behavior.
- Higher relevance and quality on a snippet should increase
  weight for the dimensions that snippet supports.

If evidence count is 0 or useful evidence count is 0, be
conservative on every dimension and use low confidence.

Confidence must be a decimal between 0.0 and 1.0 (not a percent).
Examples: 0.90 very high, 0.75 high, 0.50 moderate, 0.25 low.

Do NOT calculate overall_score or provide a recommendation.
Return ONLY valid JSON:

{{
  "company_name": "{state.company_name}",
  "growth_score": <number from 0 to 100>,
  "expansion_score": <number from 0 to 100>,
  "hiring_score": <number from 0 to 100>,
  "technology_score": <number from 0 to 100>,
  "strategic_score": <number from 0 to 100>,
  "confidence": <decimal from 0.0 to 1.0>,
  "reasons": [
    "<evidence-based reason>",
    "<evidence-based reason>",
    "<evidence-based reason>"
  ]
}}
"""

    def _get_recommendation(
        self,
        score: float,
    ) -> str:

        if score >= 75:
            return "High-priority prospect"

        if score >= 50:
            return "Potential prospect"

        return "Low-priority prospect"
