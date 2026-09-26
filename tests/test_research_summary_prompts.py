import json
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.modules.setdefault("tavily", MagicMock())

from agents.report_agent import ReportAgent
from agents.scoring_agent import ScoringAgent
from agents.state import ResearchState
from agents.research_prompt import research_summary_block
from config.schemas import Evidence


class ResearchSummaryBlockTests(unittest.TestCase):
    def test_block_includes_all_metrics(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            stop_reason="max_steps",
            avg_relevance=0.42,
            avg_quality=0.88,
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Hiring",
                url="https://example.com/h",
                content="hiring expansion",
                source="web_search",
                relevance=0.42,
                quality=0.88,
            )
        )

        block = research_summary_block(state)

        self.assertIn("Evidence count: 1", block)
        self.assertIn("Useful evidence count (relevance >= 0.35): 1", block)
        self.assertIn("Research stop reason: max_steps", block)
        self.assertIn("Average relevance: 0.42", block)
        self.assertIn("Average quality: 0.88", block)


class ScoringPromptSummaryTests(unittest.TestCase):
    def test_scoring_prompt_includes_research_summary(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            stop_reason="finish",
            useful_evidence_count=0,
        )
        captured: dict[str, str] = {}

        def fake_generate(prompt, **kwargs):
            captured["prompt"] = prompt
            return json.dumps(
                {
                    "company_name": "Acme",
                    "growth_score": 20,
                    "expansion_score": 20,
                    "hiring_score": 20,
                    "technology_score": 20,
                    "strategic_score": 20,
                    "confidence": 0.25,
                    "reasons": ["a", "b", "c"],
                }
            )

        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.side_effect = fake_generate

        agent.score(state)

        prompt = captured["prompt"]
        self.assertIn("Research summary:", prompt)
        self.assertIn("Evidence count: 0", prompt)
        self.assertIn("Useful evidence count (relevance >= 0.35): 0", prompt)
        self.assertIn("Research stop reason: finish", prompt)
        self.assertIn("0–20: no meaningful evidence", prompt)
        self.assertIn("conservatively (15 or below)", prompt)


class ReportPromptSummaryTests(unittest.TestCase):
    def test_report_prompt_includes_research_summary(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            stop_reason="search_failed_exhausted",
            avg_relevance=None,
            avg_quality=None,
            useful_evidence_count=0,
        )
        captured: dict[str, str] = {}

        agent = ReportAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(
            {
                "company_name": "Acme",
                "executive_summary": "Summary.",
                "prospect_score": 30.0,
                "recommendation": "Low-priority prospect",
                "key_signals": ["none"],
                "risks": ["Limited evidence"],
                "recommended_sales_approach": "Verify manually.",
            }
        )

        def capture_generate(prompt, **kwargs):
            captured["prompt"] = prompt
            return agent.llm.generate.return_value

        agent.llm.generate.side_effect = capture_generate

        from config.schemas import ProspectScore

        score = ProspectScore(
            company_name="Acme",
            overall_score=30.0,
            growth_score=20.0,
            expansion_score=20.0,
            hiring_score=20.0,
            technology_score=20.0,
            strategic_score=20.0,
            confidence=0.25,
            recommendation="Low-priority prospect",
            reasons=["Limited public data."],
        )

        agent.generate(state=state, score=score)

        prompt = captured["prompt"]
        self.assertIn("Research summary:", prompt)
        self.assertIn("Evidence count: 0", prompt)
        self.assertIn("Research stop reason: search_failed_exhausted", prompt)
        self.assertIn("Average relevance: n/a", prompt)
        self.assertIn("Average quality: n/a", prompt)


if __name__ == "__main__":
    unittest.main()
