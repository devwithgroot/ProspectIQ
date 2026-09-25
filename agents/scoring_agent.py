
from agents.state import ResearchState
from config.schemas import ProspectScore, ScoringAssessment
from llm.client import LLMClient


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
    ) -> ProspectScore:

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

        prompt = f"""
You are the ProspectIQ sales intelligence scoring agent.

Evaluate this company as a potential high-value B2B
sales prospect.

Company:
{state.company_name}

Research goal:
{state.research_goal}

Evidence:
{evidence_summary}

Evaluate these five dimensions independently from 0 to 100:

1. growth_score
2. expansion_score
3. hiring_score
4. technology_score
5. strategic_score

Scoring guidance:

Growth:
How strong are the company's growth signals?

Expansion:
How strong are expansion, capacity, geography,
or market-entry signals?

Hiring:
How strong are hiring and workforce-growth signals?

Technology:
How strong are technology investment,
digital transformation, or technology hiring signals?

Strategic:
How strong are acquisitions, strategic initiatives,
investments, partnerships, or major business changes?

Important rules:

- Use ONLY the provided evidence.
- Do not invent facts.
- If evidence is missing, give a conservative score.
- Stronger and higher-quality evidence should receive
  greater consideration.

Confidence must be a decimal number between 0.0 and 1.0.

Examples:
- 0.90 = very high confidence
- 0.75 = high confidence
- 0.50 = moderate confidence
- 0.25 = low confidence

DO NOT express confidence as a percentage.
For example, do NOT return 80 or 80%.
Return 0.80 instead.

Do NOT calculate overall_score.
The application will calculate the overall score.

Do NOT provide a recommendation.
The application will determine the recommendation
from the calculated overall score.

Return ONLY valid JSON using exactly this structure.

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

Do not copy placeholder values.
Calculate every score independently from the provided evidence.
"""

        response = self.llm.generate(
            prompt=prompt,
            temperature=0.0,
            max_tokens=600,
        )

        assessment = ScoringAssessment.model_validate_json(
            response
        )

        overall_score = (
            assessment.growth_score * self.GROWTH_WEIGHT
            + assessment.expansion_score * self.EXPANSION_WEIGHT
            + assessment.hiring_score * self.HIRING_WEIGHT
            + assessment.technology_score * self.TECHNOLOGY_WEIGHT
            + assessment.strategic_score * self.STRATEGIC_WEIGHT
        )

        recommendation = self._get_recommendation(
            overall_score
        )

        return ProspectScore(
            company_name=assessment.company_name,
            overall_score=overall_score,
            growth_score=assessment.growth_score,
            expansion_score=assessment.expansion_score,
            hiring_score=assessment.hiring_score,
            technology_score=assessment.technology_score,
            strategic_score=assessment.strategic_score,
            confidence=assessment.confidence,
            recommendation=recommendation,
            reasons=assessment.reasons,
        )

    def _get_recommendation(
        self,
        score: float,
    ) -> str:

        if score >= 75:
            return "High-priority prospect"

        if score >= 50:
            return "Potential prospect"

        return "Low-priority prospect"

