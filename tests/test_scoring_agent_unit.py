import json
import sys
import unittest
from unittest.mock import MagicMock

sys.modules.setdefault("tavily", MagicMock())

from agents.scoring_agent import ScoringAgent
from agents.state import ResearchState
from config.schemas import Evidence


VALID_ASSESSMENT = {
    "company_name": "Acme",
    "growth_score": 20,
    "expansion_score": 20,
    "hiring_score": 20,
    "technology_score": 20,
    "strategic_score": 20,
    "confidence": 0.9,
    "reasons": ["a", "b", "c"],
}

HIGH_LLM_ASSESSMENT = {
    "company_name": "Acme",
    "growth_score": 80,
    "expansion_score": 80,
    "hiring_score": 80,
    "technology_score": 80,
    "strategic_score": 80,
    "confidence": 0.9,
    "reasons": ["a", "b", "c"],
}


class DimensionSupportTagTests(unittest.TestCase):
    def test_technology_only_evidence_gets_technology_tag(self):
        agent = ScoringAgent()
        evidence = Evidence(
            title="Cloud program",
            url="https://example.com/t",
            content="Acme announces a cloud modernization program.",
            source="web_search",
        )
        self.assertEqual(
            agent._dimension_support_for_evidence(evidence),
            ["Technology"],
        )

    def test_hiring_and_growth_evidence_gets_multiple_tags(self):
        agent = ScoringAgent()
        evidence = Evidence(
            title="Workforce",
            url="https://example.com/h",
            content="Acme is hiring and reporting revenue growth.",
            source="web_search",
        )
        tags = agent._dimension_support_for_evidence(evidence)
        self.assertIn("Hiring", tags)
        self.assertIn("Growth", tags)


class DimensionSupportCapTests(unittest.TestCase):
    def test_technology_only_caps_unsupported_dimensions(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Cloud program",
                url="https://example.com/t",
                content="Acme announces a cloud modernization program.",
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(HIGH_LLM_ASSESSMENT)

        score = agent.score(state)

        self.assertEqual(score.technology_score, 80.0)
        self.assertEqual(score.growth_score, 15.0)
        self.assertEqual(score.expansion_score, 15.0)
        self.assertEqual(score.hiring_score, 15.0)
        self.assertEqual(score.strategic_score, 15.0)

    def test_multi_dimension_evidence_allows_multiple_high_scores(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Workforce and growth",
                url="https://example.com/h",
                content="Acme is hiring and reporting revenue growth.",
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(
            {
                "company_name": "Acme",
                "growth_score": 70,
                "expansion_score": 80,
                "hiring_score": 75,
                "technology_score": 80,
                "strategic_score": 80,
                "confidence": 0.8,
                "reasons": ["a", "b", "c"],
            }
        )

        score = agent.score(state)

        self.assertEqual(score.growth_score, 70.0)
        self.assertEqual(score.hiring_score, 75.0)
        self.assertEqual(score.expansion_score, 15.0)
        self.assertEqual(score.technology_score, 15.0)
        self.assertEqual(score.strategic_score, 15.0)

    def test_supported_dimension_preserves_llm_score(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Cloud program",
                url="https://example.com/t",
                content="Major cloud modernization and digital technology upgrade.",
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(
            {
                "company_name": "Acme",
                "growth_score": 80,
                "expansion_score": 80,
                "hiring_score": 80,
                "technology_score": 85,
                "strategic_score": 80,
                "confidence": 0.8,
                "reasons": ["a", "b", "c"],
            }
        )

        score = agent.score(state)

        self.assertEqual(score.technology_score, 85.0)


class InsufficientEvidenceGuardTests(unittest.TestCase):
    def test_empty_evidence_zeros_scores_and_low_priority(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=0,
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(HIGH_LLM_ASSESSMENT)

        score = agent.score(state)

        self.assertEqual(score.growth_score, 0.0)
        self.assertEqual(score.expansion_score, 0.0)
        self.assertEqual(score.hiring_score, 0.0)
        self.assertEqual(score.technology_score, 0.0)
        self.assertEqual(score.strategic_score, 0.0)
        self.assertEqual(score.overall_score, 0.0)
        self.assertEqual(score.recommendation, "Low-priority prospect")

    def test_zero_useful_evidence_zeros_scores_and_low_priority(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=0,
        )
        state.evidence.append(
            Evidence(
                title="About",
                url="https://www.acme.com/about",
                content="Corporate overview.",
                source="web_search",
                relevance=0.1,
                quality=1.0,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(HIGH_LLM_ASSESSMENT)

        score = agent.score(state)

        self.assertEqual(score.overall_score, 0.0)
        self.assertEqual(score.recommendation, "Low-priority prospect")
        self.assertEqual(
            (
                score.growth_score,
                score.expansion_score,
                score.hiring_score,
                score.technology_score,
                score.strategic_score,
            ),
            (0.0, 0.0, 0.0, 0.0, 0.0),
        )

    def test_useful_evidence_preserves_llm_when_all_dimensions_supported(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Broad update",
                url="https://example.com/u",
                content=(
                    "Revenue growth, geographic expansion, hiring, "
                    "cloud technology, and a strategic investment partnership."
                ),
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(HIGH_LLM_ASSESSMENT)

        score = agent.score(state)

        self.assertEqual(score.growth_score, 80.0)
        self.assertEqual(score.expansion_score, 80.0)
        self.assertEqual(score.hiring_score, 80.0)
        self.assertEqual(score.technology_score, 80.0)
        self.assertEqual(score.strategic_score, 80.0)

    def test_overall_score_matches_weighted_dimension_scores(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Hiring",
                url="https://example.com/h",
                content="hiring",
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(
            {
                "company_name": "Acme",
                "growth_score": 60,
                "expansion_score": 40,
                "hiring_score": 20,
                "technology_score": 80,
                "strategic_score": 50,
                "confidence": 0.7,
                "reasons": ["a", "b", "c"],
            }
        )

        score = agent.score(state)

        expected = (
            score.growth_score * 0.20
            + score.expansion_score * 0.25
            + score.hiring_score * 0.15
            + score.technology_score * 0.20
            + score.strategic_score * 0.20
        )
        self.assertAlmostEqual(score.overall_score, expected)


class ScoringPromptTests(unittest.TestCase):
    def test_rubric_appears_in_prompt(self):
        agent = ScoringAgent()
        prompt = agent._build_prompt(
            state=ResearchState(
                company_name="Acme",
                research_goal="Evaluate Acme.",
            ),
            evidence_summary="",
        )
        self.assertIn("0–20: no meaningful evidence", prompt)
        self.assertIn("81–100: very strong", prompt)

    def test_no_evidence_dimension_rule_in_prompt(self):
        agent = ScoringAgent()
        prompt = agent._build_prompt(
            state=ResearchState(
                company_name="Acme",
                research_goal="Evaluate Acme.",
            ),
            evidence_summary="",
        )
        self.assertIn(
            "Score a dimension above 15 only when at least one evidence",
            prompt,
        )


class ScoringConfidenceValidationTests(unittest.TestCase):
    def test_empty_evidence_clamps_confidence(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=0,
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(VALID_ASSESSMENT)

        score = agent.score(state)

        self.assertLessEqual(score.confidence, 0.35)
        self.assertEqual(score.confidence, 0.35)

    def test_useful_evidence_does_not_clamp_confidence(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Hiring",
                url="https://example.com/h",
                content="hiring expansion",
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.return_value = json.dumps(VALID_ASSESSMENT)

        score = agent.score(state)

        self.assertEqual(score.confidence, 0.9)


class ScoringJsonRetryTests(unittest.TestCase):
    def test_malformed_json_retries_successfully(self):
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            useful_evidence_count=1,
        )
        state.evidence.append(
            Evidence(
                title="Hiring",
                url="https://example.com/h",
                content="hiring",
                source="web_search",
                relevance=0.5,
                quality=0.5,
            )
        )
        calls: list[str] = []

        def fake_generate(prompt, **kwargs):
            calls.append(prompt)
            if len(calls) == 1:
                return "```json\n{not valid json\n```"
            return json.dumps(VALID_ASSESSMENT)

        agent = ScoringAgent()
        agent.llm = MagicMock()
        agent.llm.generate.side_effect = fake_generate

        score = agent.score(state)

        self.assertEqual(len(calls), 2)
        self.assertIn("not valid JSON", calls[1])
        self.assertEqual(score.confidence, 0.9)


if __name__ == "__main__":
    unittest.main()
