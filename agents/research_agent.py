from collections.abc import Callable

from tools.web_search import WebSearchTool
from agents.state import ResearchState
from llm.client import LLMClient
from llm.json_util import extract_think, parse_model, reason_lines
from config.schemas import ResearchDecision
from tools.evidence_evaluator import EvidenceEvaluator


def _one_line(text: str, limit: int = 140) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "…"


class ResearchAgent:
    def __init__(self):
        self.search_tool = WebSearchTool()
        self.evaluator = EvidenceEvaluator()
        self.llm = LLMClient()

    def run(
        self,
        state: ResearchState,
        on_progress: Callable[[str], None] | None = None,
    ) -> ResearchState:
        def note(message: str) -> None:
            if on_progress is not None and message:
                on_progress(message)

        while state.steps_taken < state.max_steps:

            print(
                f"\n[Research Agent] "
                f"Step {state.steps_taken + 1}/{state.max_steps}"
            )

            note(
                f"Choosing what to look up next on {state.company_name} "
                f"({state.steps_taken + 1}/{state.max_steps})"
            )
            decision = self.plan_next_action(state, on_progress=on_progress)

            print(
                f"[Research Agent] "
                f"Action: {decision.action}"
            )

            print(
                f"[Research Agent] "
                f"Reasoning: {decision.reasoning}"
            )
            for line in reason_lines(decision.reasoning, limit=3):
                note(line)

            if decision.action == "finish":
                print("[Research Agent] Research complete.")
                note(f"We have enough on {state.company_name} to write a briefing")
                break

            if decision.action != "search":
                print(
                    "[Research Agent] "
                    f"Unknown action: {decision.action}"
                )
                break

            if not decision.query:
                print(
                    "[Research Agent] "
                    "Search action requires a query."
                )
                break

            query = decision.query

            if self._is_duplicate_query(
                query,
                state.queries,
            ):
                print(
                    "[Research Agent] "
                    "Duplicate query detected. Finishing."
                )
                note("We already checked that, moving on")
                break

            print(
                f"[Research Agent] "
                f"Searching: {query}"
            )
            note(f"Looking up “{query}”")

            results = self.search_tool.execute(
                query=query,
                max_results=3,
            )
            note(
                f"Found {len(results)} article"
                f"{'' if len(results) == 1 else 's'} on {state.company_name}"
            )

            evaluated_results = []

            for result in results:
                title = _one_line(getattr(result, "title", "") or "", 80)
                if title:
                    note(f"Reading {title}")
                evaluated = self.evaluator.evaluate(
                    evidence=result,
                    research_goal=state.research_goal,
                )

                evaluated_results.append(evaluated)

            state.queries.append(query)
            state.evidence.extend(evaluated_results)
            state.steps_taken += 1

            print(
                f"[Research Agent] "
                f"Collected {len(results)} evidence items."
            )
            useful = [
                item
                for item in evaluated_results
                if item.relevance >= 0.35
            ]
            if useful:
                best = max(useful, key=lambda item: item.relevance)
                note(
                    f"Why: {len(useful)} of {len(evaluated_results)} "
                    f"look useful for the pitch; best is "
                    f"“{_one_line(best.title, 70)}”"
                )
            else:
                note(
                    f"Why: not much here that helps you sell to "
                    f"{state.company_name}"
                )
            note(f"Seeing what matters for the {state.company_name} pitch")

        if state.steps_taken >= state.max_steps:
            print(
                "\n[Research Agent] "
                "Maximum research steps reached."
            )
            note(f"Wrapped up the {state.company_name} research")

        if state.evidence:
            average_relevance = sum(
                e.relevance
                for e in state.evidence
            ) / len(state.evidence)

            average_quality = sum(
                e.quality
                for e in state.evidence
            ) / len(state.evidence)

            print(
                "\n[Research Agent] Research quality:"
            )

            print(
                f"[Research Agent] "
                f"Average relevance: {average_relevance:.2f}"
            )

            print(
                f"[Research Agent] "
                f"Average quality: {average_quality:.2f}"
            )

        return state

    def plan_next_action(
        self,
        state: ResearchState,
        on_progress: Callable[[str], None] | None = None,
    ) -> ResearchDecision:

        evidence_summary = "\n".join(
            [
                (
                    f"- Title: {e.title}\n"
                    f"  URL: {e.url}\n"
                    f"  Relevance: {e.relevance:.2f}\n"
                    f"  Quality: {e.quality:.2f}\n"
                    f"  Content: {e.content[:500]}"
                )
                for e in state.evidence[-10:]
            ]
        )

        previous_queries = "\n".join(
            [
                f"- {query}"
                for query in state.queries
            ]
        )

        prompt = f"""
    You are the research planning component of ProspectIQ.

    Your job is to decide the BEST next research action for
    evaluating a company as a potential high-value sales prospect.

    Company:
    {state.company_name}

    Research goal:
    {state.research_goal}

    Previous searches:
    {previous_queries}

    Evidence collected:
    {evidence_summary}

    When deciding what to do next:

    1. Do not repeat previous searches.
    2. Prefer information that is still missing.
    3. Prioritize high-value sales signals such as:
    - company growth
    - expansion
    - hiring
    - technology investment
    - funding
    - acquisitions
    - strategic initiatives
    - market position
    4. Prefer high-quality evidence.
    5. If sufficient evidence has been collected, finish the research.
    6. If evidence is weak or incomplete, search for better evidence.

    You may choose exactly one action:

    1. search
    2. finish

    If you choose "search":
    - provide exactly one focused search query.
    - the query must be different from previous searches.

    If you choose "finish":
    - query must be null.

    Return ONLY valid JSON:

    {{
    "action": "search" or "finish",
    "query": "search query or null",
    "reasoning": "2-3 sentences: what you already know, what is still missing, and why this next action"
    }}
    """

        response = self.llm.generate(
            prompt=prompt,
            temperature=0.0,
            max_tokens=400,
        )
        if on_progress is not None:
            for line in reason_lines(extract_think(response), limit=2):
                on_progress(line)

        return parse_model(ResearchDecision, response)

    def _is_duplicate_query(
        self,
        query: str,
        previous_queries: list[str],
    ) -> bool:

        normalized_query = query.strip().lower()

        return any(
            normalized_query == previous.strip().lower()
            for previous in previous_queries
        )

