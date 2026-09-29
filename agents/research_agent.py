from collections.abc import Callable

from tools.web_search import WebSearchTool
from agents.state import ResearchState
from llm.client import LLMClient
from llm.json_util import extract_think, parse_model, reason_lines
from config.research_log import get_logger
from config.schemas import ResearchDecision
from tools.evidence_evaluator import EvidenceEvaluator

log = get_logger("research")


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

            log.info(
                "Step %s/%s company=%s",
                state.steps_taken + 1,
                state.max_steps,
                state.company_name,
            )

            note(f"Choosing what to look up next on {state.company_name}")
            decision = self.plan_next_action(state, on_progress=on_progress)

            log.info("Action=%s query=%r", decision.action, decision.query)
            log.info("Reasoning: %s", decision.reasoning)
            for line in reason_lines(decision.reasoning, limit=3):
                note(line)

            if decision.action == "finish":
                log.info("Research complete for %s", state.company_name)
                note(f"We have enough on {state.company_name} to write a briefing")
                break

            if decision.action != "search":
                log.warning("Unknown action: %s", decision.action)
                break

            if not decision.query:
                log.warning("Search action missing query")
                break

            query = decision.query

            if self._is_duplicate_query(
                query,
                state.queries,
            ):
                log.info("Duplicate query, finishing: %s", query)
                note("We already checked that, moving on")
                break

            log.info("Searching: %s", query)
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

            log.info("Collected %s evidence items", len(results))
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
            log.info("Maximum research steps reached for %s", state.company_name)
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

            log.info(
                "Quality company=%s relevance=%.2f quality=%.2f evidence=%s",
                state.company_name,
                average_relevance,
                average_quality,
                len(state.evidence),
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
    - leadership and decision makers (who to talk to)
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

    def lookup_person(
        self,
        *,
        full_name: str,
        company_name: str,
        title: str,
        research_goal: str,
        on_progress: Callable[[str], None] | None = None,
    ) -> list:
        def note(message: str) -> None:
            if on_progress is not None and message:
                on_progress(message)

        query = f'"{full_name}" {company_name} {title}'.strip()
        note(f"Looking up {full_name} at {company_name}")
        try:
            results = self.search_tool.execute(query=query, max_results=3)
        except Exception as exc:
            log.exception("Person search failed for %s (%s)", full_name, exc)
            note(f"Couldn’t find public articles on {full_name}")
            return []

        note(
            f"Found {len(results)} article"
            f"{'' if len(results) == 1 else 's'} on {full_name}"
        )
        evaluated = []
        for result in results:
            headline = _one_line(getattr(result, "title", "") or "", 80)
            if headline:
                note(f"Reading {headline}")
            evaluated.append(
                self.evaluator.evaluate(
                    evidence=result,
                    research_goal=research_goal,
                )
            )
        useful = [item for item in evaluated if item.relevance >= 0.35]
        if useful:
            best = max(useful, key=lambda item: item.relevance)
            note(
                f"Why: {len(useful)} of {len(evaluated)} "
                f"look useful for {full_name}; best is "
                f"“{_one_line(best.title, 70)}”"
            )
        else:
            note(f"Why: not much public detail yet on {full_name}")
        return evaluated

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

