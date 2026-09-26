import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("tavily", MagicMock())

from app.orchestrator import ProspectIQ
from app.prospect_upload import company_domain_from_website
from config.schemas import Evidence, ProspectReport, ProspectScore
from tools.evidence_evaluator import EvidenceEvaluator


class CompanyDomainFromWebsiteTests(unittest.TestCase):
    def test_https_with_www(self):
        self.assertEqual(
            company_domain_from_website("https://www.acme.com/about"),
            "acme.com",
        )

    def test_bare_domain(self):
        self.assertEqual(company_domain_from_website("acme.com"), "acme.com")

    def test_empty(self):
        self.assertIsNone(company_domain_from_website(None))
        self.assertIsNone(company_domain_from_website("   "))


class CompanyDomainQualityTests(unittest.TestCase):
    def test_matching_company_url_quality_one(self):
        evaluator = EvidenceEvaluator()
        scored = evaluator.evaluate(
            Evidence(
                title="Investor relations",
                url="https://www.acme.com/investors",
                content="Acme Corp growth and hiring plans.",
                source="web_search",
            ),
            research_goal="Evaluate Acme as a sales prospect.",
            company_domain="acme.com",
        )
        self.assertEqual(scored.quality, 1.0)


class AnalyzeWiringTests(unittest.TestCase):
    def test_analyze_passes_company_domain_into_research_state(self):
        app = ProspectIQ()
        captured: dict[str, str | None] = {}

        def capture_run(state, on_progress=None):
            captured["company_domain"] = state.company_domain
            return state

        app.research_agent.run = MagicMock(side_effect=capture_run)
        app.scoring_agent.score = MagicMock(
            return_value=ProspectScore(
                company_name="Acme",
                overall_score=50.0,
                growth_score=50.0,
                expansion_score=50.0,
                hiring_score=50.0,
                technology_score=50.0,
                strategic_score=50.0,
                confidence=0.5,
                recommendation="Potential prospect",
                reasons=["test"],
            )
        )
        app.report_agent.generate = MagicMock(
            return_value=ProspectReport(
                company_name="Acme",
                executive_summary="Summary.",
                prospect_score=50.0,
                recommendation="Potential prospect",
                key_signals=["signal"],
                risks=["risk"],
                recommended_sales_approach="Approach.",
            )
        )

        app.analyze(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            company_domain="acme.com",
        )

        self.assertEqual(captured["company_domain"], "acme.com")
        app.research_agent.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
