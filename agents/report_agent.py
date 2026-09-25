from agents.state import ResearchState
from config.schemas import ProspectReport, ProspectScore
from llm.client import LLMClient


class ReportAgent:

    def __init__(self):
        self.llm = LLMClient()

    def generate(
        self,
        state: ResearchState,
        score: ProspectScore,
    ) -> ProspectReport:

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
You are the ProspectIQ report generation agent.

Create a concise B2B sales intelligence report
for the salesperson reviewing this prospect.

Company:
{state.company_name}

Research goal:
{state.research_goal}

Final prospect score:
{score.overall_score:.1f}

Recommendation:
{score.recommendation}

Dimension scores:

Growth: {score.growth_score:.1f}
Expansion: {score.expansion_score:.1f}
Hiring: {score.hiring_score:.1f}
Technology: {score.technology_score:.1f}
Strategic: {score.strategic_score:.1f}

Confidence:
{score.confidence:.2f}

Scoring reasons:
{chr(10).join(f"- {reason}" for reason in score.reasons)}

Research evidence:
{evidence_summary}

Your job is to explain the assessment to a salesperson.

Generate:

1. executive_summary
Explain in 2-4 sentences why this company
is or is not a valuable prospect.

2. key_signals
List the strongest buying or business signals
supported by the evidence.

3. risks
List important risks, uncertainties, or missing
information that a salesperson should consider.

4. recommended_sales_approach
Give a practical sales approach based ONLY on
the evidence and scoring information.

Important rules:

- Use ONLY the provided information.
- Do not invent facts.
- Do not change the prospect score.
- Do not change the recommendation.
- Do not invent sources or URLs.
- If information is missing, explicitly say so.
- Keep the report useful for a B2B salesperson.

Return ONLY valid JSON.

{{
  "company_name": "{state.company_name}",
  "executive_summary": "...",
  "prospect_score": {score.overall_score:.1f},
  "recommendation": "{score.recommendation}",
  "key_signals": [
    "...",
    "...",
    "..."
  ],
  "risks": [
    "...",
    "..."
  ],
  "recommended_sales_approach": "...",
}}
"""

        response = self.llm.generate(
            prompt=prompt,
            temperature=0.0,
            max_tokens=800,
        )

        report_data = ProspectReport.model_validate_json(
            response
        )

        report_data.prospect_score = score.overall_score
        report_data.recommendation = score.recommendation
        report_data.evidence = state.evidence

        return report_data