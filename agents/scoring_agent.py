from collections.abc import Callable

from agents.state import ResearchState
from agents.research_prompt import research_summary_block
from config.schemas import ProspectScore, ScoringAssessment
from llm.client import LLMClient
from llm.json_util import generate_model, reason_lines

INSUFFICIENT_EVIDENCE_CONFIDENCE_CAP = 0.35


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

        evidence_summary = "\n".join(
            [
                (
                    f"- Title: {e.title}\n"
                    f"  URL: {e.url}\n"
                    f"  Relevance: {e.relevance:.2f}\n"
                    f"  Quality: {e.quality:.2f}\n"
                    f"  Content: {e.content[:700]}"
                )
                for e in state.evidence
            ]
        )

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

    def _guarded_dimension_scores(
        self,
        state: ResearchState,
        assessment: ScoringAssessment,
    ) -> tuple[float, float, float, float, float]:
        if len(state.evidence) == 0 or state.useful_evidence_count == 0:
            return (0.0, 0.0, 0.0, 0.0, 0.0)
        return (
            assessment.growth_score,
            assessment.expansion_score,
            assessment.hiring_score,
            assessment.technology_score,
            assessment.strategic_score,
        )

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
