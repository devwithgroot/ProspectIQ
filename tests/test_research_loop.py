import sys
import unittest
from unittest.mock import MagicMock, patch

# Allow importing ResearchAgent without Tavily installed in test env.
sys.modules.setdefault("tavily", MagicMock())

from agents.research_agent import ResearchAgent, _normalize_url
from agents.state import ResearchState
from config.schemas import Evidence, ResearchDecision
from tools.evidence_evaluator import EvidenceEvaluator


def _hiring_evidence(
    *,
    url: str = "https://news.example.com/hiring",
    title: str = "Company hiring expansion",
) -> Evidence:
    return Evidence(
        title=title,
        url=url,
        content=(
            "The company announced hiring and expansion with new "
            "technology investment and strategic growth initiatives."
        ),
        source="web_search",
        evidence_type="web",
    )


class EvidenceKeepRuleTests(unittest.TestCase):
    def _agent(self) -> ResearchAgent:
        with patch.object(ResearchAgent, "__init__", lambda self: None):
            return ResearchAgent()

    def _state(
        self,
        *,
        company_name: str = "Acme Corp",
        company_domain: str | None = "acme.com",
    ) -> ResearchState:
        return ResearchState(
            company_name=company_name,
            research_goal="Evaluate Acme as a sales prospect.",
            company_domain=company_domain,
        )

    def test_high_quality_unrelated_reuters_dropped(self):
        agent = self._agent()
        evidence = Evidence(
            title="Global markets wrap",
            url="https://www.reuters.com/world/macro-story",
            content="Central banks and inflation across regions.",
            source="web_search",
            relevance=0.0,
            quality=0.9,
        )
        self.assertFalse(agent._should_keep(evidence, self._state()))

    def test_company_domain_url_kept_at_zero_relevance(self):
        agent = self._agent()
        evidence = Evidence(
            title="About us",
            url="https://www.acme.com/about",
            content="Welcome to our corporate site.",
            source="web_search",
            relevance=0.0,
            quality=1.0,
        )
        self.assertTrue(agent._should_keep(evidence, self._state()))

    def test_high_quality_with_company_name_kept(self):
        agent = self._agent()
        evidence = Evidence(
            title="Acme Corp expands in Europe",
            url="https://www.reuters.com/business/acme-europe",
            content="Acme Corp said it will open new offices.",
            source="web_search",
            relevance=0.0,
            quality=0.9,
        )
        self.assertTrue(agent._should_keep(evidence, self._state()))

    def test_relevance_path_keeps_mid_quality(self):
        agent = self._agent()
        evidence = Evidence(
            title="Industry note",
            url="https://blog.example.com/post",
            content="General industry commentary.",
            source="web_search",
            relevance=0.40,
            quality=0.5,
        )
        self.assertTrue(agent._should_keep(evidence, self._state()))


class ResearchLoopTests(unittest.TestCase):
    def _agent_with_mocks(self) -> ResearchAgent:
        with patch.object(ResearchAgent, "__init__", lambda self: None):
            agent = ResearchAgent()
        agent.search_tool = MagicMock()
        agent.evaluator = EvidenceEvaluator()
        agent.llm = MagicMock()
        return agent

    def test_duplicate_query_replans_without_extra_search(self):
        agent = self._agent_with_mocks()
        agent.search_tool.execute.return_value = [_hiring_evidence()]

        decisions = [
            ResearchDecision(
                action="search",
                query="Acme hiring",
                reasoning="Need hiring signals.",
            ),
            ResearchDecision(
                action="search",
                query="Acme hiring",
                reasoning="Repeat.",
            ),
            ResearchDecision(
                action="finish",
                query=None,
                reasoning="Enough evidence.",
            ),
        ]
        agent.plan_next_action = MagicMock(side_effect=decisions)

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme as a sales prospect.",
            max_steps=3,
        )
        final = agent.run(state)

        self.assertEqual(final.stop_reason, "finish")
        self.assertEqual(final.steps_taken, 1)
        agent.search_tool.execute.assert_called_once()

    def test_max_steps_stop_reason(self):
        agent = self._agent_with_mocks()
        agent.search_tool.execute.return_value = [_hiring_evidence()]

        queries = ["q1", "q2", "q3"]
        decisions = [
            ResearchDecision(
                action="search",
                query=query,
                reasoning="Search.",
            )
            for query in queries
        ]
        agent.plan_next_action = MagicMock(side_effect=decisions)

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme as a sales prospect.",
            max_steps=3,
        )
        final = agent.run(state)

        self.assertEqual(final.steps_taken, 3)
        self.assertEqual(final.stop_reason, "max_steps")
        self.assertEqual(agent.search_tool.execute.call_count, 3)

    def test_empty_search_does_not_consume_step(self):
        agent = self._agent_with_mocks()
        agent.search_tool.execute.side_effect = [
            [],
            [_hiring_evidence()],
        ]

        decisions = [
            ResearchDecision(
                action="search",
                query="empty query",
                reasoning="Try.",
            ),
            ResearchDecision(
                action="search",
                query="better query",
                reasoning="Retry.",
            ),
            ResearchDecision(
                action="finish",
                query=None,
                reasoning="Done.",
            ),
        ]
        agent.plan_next_action = MagicMock(side_effect=decisions)

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme as a sales prospect.",
            max_steps=2,
        )
        final = agent.run(state)

        self.assertEqual(final.steps_taken, 1)
        self.assertEqual(len(final.queries), 2)

    def test_url_dedupe_keeps_single_entry(self):
        agent = self._agent_with_mocks()
        url = "https://news.example.com/same"
        agent.search_tool.execute.side_effect = [
            [_hiring_evidence(url=url)],
            [_hiring_evidence(url=url, title="Same story again")],
        ]

        decisions = [
            ResearchDecision(
                action="search",
                query="query one",
                reasoning="One.",
            ),
            ResearchDecision(
                action="search",
                query="query two",
                reasoning="Two.",
            ),
            ResearchDecision(
                action="finish",
                query=None,
                reasoning="Done.",
            ),
        ]
        agent.plan_next_action = MagicMock(side_effect=decisions)

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme as a sales prospect.",
            max_steps=3,
        )
        final = agent.run(state)

        self.assertEqual(len(final.evidence), 1)

    def test_search_failure_replans(self):
        agent = self._agent_with_mocks()
        agent.search_tool.execute.side_effect = [
            RuntimeError("network"),
            [_hiring_evidence()],
        ]

        decisions = [
            ResearchDecision(
                action="search",
                query="fail query",
                reasoning="Try.",
            ),
            ResearchDecision(
                action="search",
                query="ok query",
                reasoning="Retry.",
            ),
            ResearchDecision(
                action="finish",
                query=None,
                reasoning="Done.",
            ),
        ]
        agent.plan_next_action = MagicMock(side_effect=decisions)

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme as a sales prospect.",
            max_steps=2,
        )
        final = agent.run(state)

        self.assertEqual(final.stop_reason, "finish")
        self.assertEqual(final.steps_taken, 1)

    def test_finish_with_zero_evidence_requires_search_first(self):
        agent = self._agent_with_mocks()
        agent.search_tool.execute.return_value = [_hiring_evidence()]

        decisions = [
            ResearchDecision(
                action="finish",
                query=None,
                reasoning="Too early.",
            ),
            ResearchDecision(
                action="search",
                query="Acme growth",
                reasoning="Search first.",
            ),
            ResearchDecision(
                action="finish",
                query=None,
                reasoning="Now done.",
            ),
        ]
        agent.plan_next_action = MagicMock(side_effect=decisions)

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme as a sales prospect.",
            max_steps=2,
        )
        final = agent.run(state)

        self.assertEqual(final.stop_reason, "finish")
        self.assertGreaterEqual(len(final.evidence), 1)

    def test_max_steps_zero_skips_research(self):
        agent = self._agent_with_mocks()
        agent.plan_next_action = MagicMock()

        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
            max_steps=0,
        )
        final = agent.run(state)

        self.assertEqual(final.stop_reason, "max_steps")
        agent.plan_next_action.assert_not_called()
        agent.search_tool.execute.assert_not_called()

    def test_finalize_metrics(self):
        agent = self._agent_with_mocks()
        state = ResearchState(
            company_name="Acme",
            research_goal="Evaluate Acme.",
        )
        evaluated = agent.evaluator.evaluate(
            _hiring_evidence(),
            research_goal=state.research_goal,
            company_name=state.company_name,
        )
        state.evidence.append(evaluated)
        agent._finalize_metrics(state)

        self.assertIsNotNone(state.avg_relevance)
        self.assertIsNotNone(state.avg_quality)
        self.assertGreaterEqual(state.useful_evidence_count, 1)


class EvidenceEvaluatorTests(unittest.TestCase):
    def test_signal_content_scores_higher_than_generic_goal_wording(self):
        evaluator = EvidenceEvaluator()
        signal = evaluator.evaluate(
            _hiring_evidence(),
            research_goal="Determine whether Acme is a high-value sales prospect.",
        )
        generic = evaluator.evaluate(
            Evidence(
                title="About us",
                url="https://blog.example.com/about",
                content="We are a company that helps customers learn about us.",
                source="web_search",
            ),
            research_goal="Determine whether Acme is a high-value sales prospect.",
        )

        self.assertGreater(signal.relevance, generic.relevance)

    def test_company_domain_quality_not_hardcoded(self):
        evaluator = EvidenceEvaluator()
        scored = evaluator.evaluate(
            Evidence(
                title="Investor relations",
                url="https://www.acmecorp.com/investors",
                content="Acme Corp growth and hiring plans.",
                source="web_search",
            ),
            research_goal="Evaluate Acme.",
            company_domain="acmecorp.com",
        )

        self.assertEqual(scored.quality, 1.0)

    def test_supermarket_does_not_match_market(self):
        evaluator = EvidenceEvaluator()
        score = evaluator._calculate_signal_relevance(
            "visit our supermarket locator"
        )
        self.assertEqual(score, 0.0)

    def test_expansion_plan_counts_one_signal(self):
        evaluator = EvidenceEvaluator()
        score = evaluator._calculate_signal_relevance(
            "our expansion plan for next year"
        )
        self.assertAlmostEqual(score, 0.25)

    def test_ceo_announced_hiring_counts_two_signals(self):
        evaluator = EvidenceEvaluator()
        score = evaluator._calculate_signal_relevance(
            "ceo announced hiring"
        )
        self.assertAlmostEqual(score, 0.5)

    def test_four_distinct_signals_reach_keep_threshold(self):
        evaluator = EvidenceEvaluator()
        scored = evaluator.evaluate(
            Evidence(
                title="Update",
                url="https://news.example.com/update",
                content=(
                    "Reports growth in hiring with new funding "
                    "and technology plans."
                ),
                source="web_search",
            ),
            research_goal="Go.",
        )
        self.assertAlmostEqual(scored.relevance, 0.7)
        self.assertGreaterEqual(scored.relevance, 0.35)


class ResearchDecisionTests(unittest.TestCase):
    def test_action_normalized_to_lowercase(self):
        decision = ResearchDecision(
            action="Search",
            query="Acme hiring",
            reasoning="Need signals.",
        )
        self.assertEqual(decision.action, "search")


class NormalizeUrlTests(unittest.TestCase):
    def test_strips_fragment_and_trailing_slash(self):
        self.assertEqual(
            _normalize_url("https://Example.com/path/#section"),
            "https://example.com/path",
        )


if __name__ == "__main__":
    unittest.main()
