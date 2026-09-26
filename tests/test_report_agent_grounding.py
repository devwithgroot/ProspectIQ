import json
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("tavily", MagicMock())

from agents.report_agent import ReportAgent
from agents.report_grounding import EXECUTIVE_SUMMARY_CAVEAT
from agents.state import ResearchState
from config.schemas import Evidence, ProspectScore


def _cloud_evidence() -> Evidence:
    return Evidence(
        title="Cloud hiring program",
        url="https://example.com/cloud",
        content="Acme announces cloud modernization and active hiring for engineers.",
        source="web_search",
        relevance=0.7,
        quality=0.8,
    )


def _score(**overrides) -> ProspectScore:
    base = dict(
        company_name="Acme",
        overall_score=55.0,
        growth_score=40.0,
        expansion_score=15.0,
        hiring_score=60.0,
        technology_score=70.0,
        strategic_score=15.0,
        confidence=0.6,
        recommendation="Potential prospect",
        reasons=["Hiring and cloud investment noted."],
    )
    base.update(overrides)
    return ProspectScore(**base)


def _llm_json(**fields) -> str:
    payload = {
        "company_name": "Acme",
        "executive_summary": "Acme shows moderate potential.",
        "prospect_score": 99.0,
        "recommendation": "High-priority prospect",
        "key_signals": ["Cloud modernization underway."],
        "risks": ["Limited evidence"],
        "recommended_sales_approach": "Lead with cloud hiring themes.",
    }
    payload.update(fields)
    return json.dumps(payload)


class ReportAgentGroundingTests(unittest.TestCase):
    def _run_report(
        self,
        state: ResearchState,
        score: ProspectScore,
        llm_fields: dict,
    ):
        agent = ReportAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = _llm_json(**llm_fields)
        return agent.generate(state=state, score=score)

    def test_hallucinated_signal_removed(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())

        report = self._run_report(
            state,
            _score(),
            {
                "key_signals": [
                    "Acme acquired rival Corp for two billion dollars.",
                    "Cloud modernization and hiring for engineers.",
                ],
            },
        )

        self.assertEqual(len(report.key_signals), 1)
        self.assertIn("cloud", report.key_signals[0].lower())

    def test_paraphrase_signal_retained(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())

        report = self._run_report(
            state,
            _score(),
            {
                "key_signals": [
                    "Engineering hiring supports cloud modernization plans.",
                ],
            },
        )

        self.assertEqual(len(report.key_signals), 1)
        self.assertIn("engineering", report.key_signals[0].lower())

    def test_unsupported_dimension_signal_removed(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())

        report = self._run_report(
            state,
            _score(),
            {
                "key_signals": [
                    "Major geographic expansion across European markets.",
                    "Cloud modernization and hiring for engineers.",
                ],
            },
        )

        self.assertEqual(len(report.key_signals), 1)
        self.assertNotIn("european", report.key_signals[0].lower())

    def test_meta_risk_retained_without_evidence_overlap(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=0,
            stop_reason="search_failed_exhausted",
        )

        report = self._run_report(
            state,
            _score(confidence=0.25, recommendation="Low-priority prospect"),
            {
                "risks": [
                    "Limited public evidence; hiring plans remain unclear.",
                ],
            },
        )

        self.assertEqual(len(report.risks), 1)
        self.assertIn("limited public", report.risks[0].lower())

    def test_invented_risk_removed(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())

        report = self._run_report(
            state,
            _score(),
            {
                "risks": [
                    "Opening fifty offices across EMEA next quarter.",
                    "Limited evidence on budget ownership.",
                ],
            },
        )

        self.assertEqual(len(report.risks), 1)
        self.assertIn("limited evidence", report.risks[0].lower())
        self.assertNotIn("emea", report.risks[0].lower())

    def test_mixed_sales_approach_keeps_grounded_sentences_only(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())

        report = self._run_report(
            state,
            _score(),
            {
                "recommended_sales_approach": (
                    "Reference their cloud modernization and engineering hiring. "
                    "Offer a free global data center tour next week."
                ),
            },
        )

        approach = report.recommended_sales_approach.lower()
        self.assertIn("cloud", approach)
        self.assertIn("hiring", approach)
        self.assertNotIn("data center", approach)

    def test_executive_summary_appends_caveat_for_unsupported_sentence(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())

        report = self._run_report(
            state,
            _score(),
            {
                "executive_summary": (
                    "Acme is a strong prospect. "
                    "They will open fifty offices across EMEA next quarter."
                ),
            },
        )

        self.assertIn(EXECUTIVE_SUMMARY_CAVEAT, report.executive_summary)

    def test_score_and_recommendation_overwrite_preserved(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(_cloud_evidence())
        score = _score(
            overall_score=55.0,
            recommendation="Potential prospect",
        )

        report = self._run_report(
            state,
            score,
            {
                "prospect_score": 99.0,
                "recommendation": "High-priority prospect",
            },
        )

        self.assertEqual(report.prospect_score, 55.0)
        self.assertEqual(report.recommendation, "Potential prospect")

    def test_zero_evidence_uses_fallbacks(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=0,
            stop_reason="max_steps",
        )
        score = _score(
            overall_score=10.0,
            recommendation="Low-priority prospect",
            growth_score=0.0,
            expansion_score=0.0,
            hiring_score=0.0,
            technology_score=0.0,
            strategic_score=0.0,
        )

        report = self._run_report(
            state,
            score,
            {
                "key_signals": ["Aggressive expansion across Asia-Pacific."],
                "risks": ["They already signed a ten-year competitor contract."],
                "recommended_sales_approach": (
                    "Pitch enterprise-wide replacement on day one."
                ),
                "executive_summary": (
                    "Acme is expanding rapidly across Asia-Pacific markets."
                ),
            },
        )

        self.assertEqual(len(report.key_signals), 1)
        self.assertIn("No specific buying signals", report.key_signals[0])
        self.assertIn("useful evidence item(s)", report.key_signals[0])
        self.assertIn("Limited research evidence", report.risks[0])
        self.assertIn("Low-priority prospect", report.recommended_sales_approach)
        self.assertIn(EXECUTIVE_SUMMARY_CAVEAT, report.executive_summary)
        self.assertEqual(len(report.evidence), 0)


if __name__ == "__main__":
    unittest.main()
