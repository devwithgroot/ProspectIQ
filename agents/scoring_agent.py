
from agents.state import ResearchState
from config.schemas import ProspectScore
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
- Confidence must reflect how much reliable evidence
  supports your assessment.
- Do NOT calculate overall_score.
- The application will calculate the overall score.

Recommendation must be one of:

- "High-priority prospect"
- "Potential prospect"
- "Low-priority prospect"

Return ONLY valid JSON:

{{
  "company_name": "{state.company_name}",
  "overall_score": 0,
  "growth_score": 0,
  "expansion_score": 0,
  "hiring_score": 0,
  "technology_score": 0,
  "strategic_score": 0,
  "confidence": 0,
  "recommendation": "...",
  "reasons": [
    "...",
    "...",
    "..."
  ]
}}
"""

        response = self.llm.generate(
            prompt=prompt,
            temperature=0.0,
            max_tokens=600,
        )

        result = ProspectScore.model_validate_json(
            response
        )

        result.overall_score = (
            result.growth_score * self.GROWTH_WEIGHT
            + result.expansion_score * self.EXPANSION_WEIGHT
            + result.hiring_score * self.HIRING_WEIGHT
            + result.technology_score * self.TECHNOLOGY_WEIGHT
            + result.strategic_score * self.STRATEGIC_WEIGHT
        )

        result.recommendation = self._get_recommendation(
            result.overall_score
        )

        return result

    def _get_recommendation(
        self,
        score: float,
    ) -> str:

        if score >= 75:
            return "High-priority prospect"

        if score >= 50:
            return "Potential prospect"

        return "Low-priority prospect"

