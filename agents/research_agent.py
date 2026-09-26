from collections.abc import Callable

from pydantic import ValidationError

from tools.web_search import WebSearchTool
from agents.state import ResearchState
from llm.client import LLMClient
from llm.json_util import extract_think, parse_model, reason_lines
from config.schemas import Evidence, ResearchDecision
from tools.evidence_evaluator import EvidenceEvaluator


def _one_line(text: str, limit: int = 140) -> str:
    cleaned = " ".join((text or "").split())
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "…"


def _normalize_url(url: str) -> str:
    normalized = (url or "").strip().lower()
    if "#" in normalized:
        normalized = normalized.split("#", 1)[0]
    normalized = normalized.rstrip("/")
    return normalized


class ResearchAgent:
    USEFUL_RELEVANCE = 0.35
    KEEP_RELEVANCE = 0.35
    KEEP_QUALITY = 0.85
    MAX_GUARD_RAIL_FAILURES = 5
    NEAR_DUPLICATE_JACCARD = 0.85

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

        if state.max_steps < 1:
            state.stop_reason = "max_steps"
            note("Skipping web research (step budget is zero).")
            return state

        guard_failures = 0
        last_guard_reason: str | None = None
        planner_feedback = ""

        while state.steps_taken < state.max_steps:
            remaining = state.max_steps - state.steps_taken

            print(
                f"\n[Research Agent] "
                f"Step {state.steps_taken + 1}/{state.max_steps}"
            )

            note(f"Choosing what to look up next on {state.company_name}")
            decision = self.plan_next_action(
                state,
                planner_feedback=planner_feedback,
                on_progress=on_progress,
            )
            planner_feedback = ""

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

            action = (decision.action or "").strip().lower()

            if action == "finish":
                if not state.evidence and remaining > 0:
                    planner_feedback = (
                        "You must run at least one successful search "
                        "before finishing. Choose search with a focused query."
                    )
                    guard_failures, last_guard_reason = self._record_guard_failure(
                        guard_failures,
                        "invalid_planner_exhausted",
                    )
                    if guard_failures >= self.MAX_GUARD_RAIL_FAILURES:
                        state.stop_reason = last_guard_reason
                        break
                    continue

                print("[Research Agent] Research complete.")
                note(f"We have enough on {state.company_name} to write a briefing")
                state.stop_reason = "finish"
                break

            if action != "search":
                print(
                    "[Research Agent] "
                    f"Unknown action: {decision.action}"
                )
                planner_feedback = (
                    f'Unknown action "{decision.action}". '
                    'Use "search" or "finish" only.'
                )
                guard_failures, last_guard_reason = self._record_guard_failure(
                    guard_failures,
                    "invalid_planner_exhausted",
                )
                if guard_failures >= self.MAX_GUARD_RAIL_FAILURES:
                    state.stop_reason = last_guard_reason
                    break
                continue

            query = (decision.query or "").strip()
            if not query:
                print(
                    "[Research Agent] "
                    "Search action requires a query."
                )
                planner_feedback = (
                    "Search action requires a non-empty query."
                )
                guard_failures, last_guard_reason = self._record_guard_failure(
                    guard_failures,
                    "invalid_planner_exhausted",
                )
                if guard_failures >= self.MAX_GUARD_RAIL_FAILURES:
                    state.stop_reason = last_guard_reason
                    break
                continue

            if self._is_duplicate_query(query, state.queries):
                print(
                    "[Research Agent] "
                    "Duplicate query detected; replanning."
                )
                note("We already checked that — picking a different angle")
                planner_feedback = (
                    f'Your query duplicated a previous search: "{query}". '
                    "Choose a different query or finish."
                )
                guard_failures, last_guard_reason = self._record_guard_failure(
                    guard_failures,
                    "duplicate_query_exhausted",
                )
                if guard_failures >= self.MAX_GUARD_RAIL_FAILURES:
                    state.stop_reason = last_guard_reason
                    break
                continue

            guard_failures = 0
            last_guard_reason = None

            print(
                f"[Research Agent] "
                f"Searching: {query}"
            )
            note(f"Looking up “{query}”")

            try:
                results = self.search_tool.execute(
                    query=query,
                    max_results=3,
                )
            except Exception as exc:
                print(f"[Research Agent] Search failed ({exc})")
                note(f"Search failed for {state.company_name}; trying another angle")
                planner_feedback = (
                    f"Last search failed ({exc}). "
                    "Try a different query."
                )
                guard_failures, last_guard_reason = self._record_guard_failure(
                    guard_failures,
                    "search_failed_exhausted",
                )
                if guard_failures >= self.MAX_GUARD_RAIL_FAILURES:
                    state.stop_reason = last_guard_reason
                    break
                continue

            note(
                f"Found {len(results)} article"
                f"{'' if len(results) == 1 else 's'} on {state.company_name}"
            )

            if not results:
                state.queries.append(query)
                planner_feedback = (
                    f'Last search returned no results for: "{query}". '
                    "Try a different query."
                )
                note("Nothing came back — will try a different search")
                continue

            evaluated_results = []

            for result in results:
                title = _one_line(getattr(result, "title", "") or "", 80)
                if title:
                    note(f"Reading {title}")
                evaluated = self.evaluator.evaluate(
                    evidence=result,
                    research_goal=state.research_goal,
                    company_name=state.company_name,
                    company_domain=state.company_domain,
                )

                evaluated_results.append(evaluated)

            kept = self._merge_evidence(state, evaluated_results)

            state.queries.append(query)
            state.steps_taken += 1

            print(
                f"[Research Agent] "
                f"Collected {len(kept)} evidence items "
                f"({len(evaluated_results)} evaluated)."
            )
            useful = [
                item
                for item in evaluated_results
                if item.relevance >= self.USEFUL_RELEVANCE
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

        if state.stop_reason is None and state.steps_taken >= state.max_steps:
            print(
                "\n[Research Agent] "
                "Maximum research steps reached."
            )
            note(f"Wrapped up the {state.company_name} research")
            state.stop_reason = "max_steps"

        self._finalize_metrics(state)

        if state.evidence:
            print(
                "\n[Research Agent] Research quality:"
            )

            print(
                f"[Research Agent] "
                f"Average relevance: {state.avg_relevance:.2f}"
            )

            print(
                f"[Research Agent] "
                f"Average quality: {state.avg_quality:.2f}"
            )

        return state

    def plan_next_action(
        self,
        state: ResearchState,
        *,
        planner_feedback: str = "",
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

        evidence_index = "\n".join(
            [
                f"- {_one_line(e.title, 80)} ({e.url})"
                for e in state.evidence
            ]
        ) or "(none)"

        previous_queries = "\n".join(
            [
                f"- {query}"
                for query in state.queries
            ]
        ) or "(none)"

        remaining = state.max_steps - state.steps_taken
        feedback_block = ""
        if planner_feedback:
            feedback_block = f"""
    Planner feedback (must address this):
    {planner_feedback}
    """

        prompt = f"""
    You are the research planning component of ProspectIQ.

    Your job is to decide the BEST next research action for
    evaluating a company as a potential high-value sales prospect.

    Research budget:
    - Steps taken: {state.steps_taken}
    - Maximum searches: {state.max_steps}
    - Remaining searches: {remaining}

    Company:
    {state.company_name}

    Research goal:
    {state.research_goal}

    Previous searches:
    {previous_queries}

    All evidence URLs collected:
    {evidence_index}

    Recent evidence (detail):
    {evidence_summary or "(none)"}
    {feedback_block}
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
    4. Relevance and quality scores are automated heuristics about
       sales signals, not goal wording alone.
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

        last_error: Exception | None = None
        for attempt in range(2):
            retry_prompt = prompt
            if attempt == 1 and last_error is not None:
                retry_prompt = (
                    prompt
                    + "\n\nYour previous answer was not valid JSON. "
                    "Return ONLY valid JSON. No markdown. No extra text."
                )

            response = self.llm.generate(
                prompt=retry_prompt,
                temperature=0.0,
                max_tokens=400,
            )
            if on_progress is not None:
                for line in reason_lines(extract_think(response), limit=2):
                    on_progress(line)

            try:
                return parse_model(ResearchDecision, response)
            except (ValidationError, ValueError) as exc:
                last_error = exc

        raise ValueError(
            f"LLM did not return valid ResearchDecision JSON: {last_error}"
        )

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
            print(f"[Research Agent] Person search failed ({exc})")
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
                    company_name=company_name,
                )
            )
        useful = [
            item
            for item in evaluated
            if item.relevance >= self.USEFUL_RELEVANCE
        ]
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

    def _should_keep(self, evidence: Evidence) -> bool:
        return (
            evidence.relevance >= self.KEEP_RELEVANCE
            or evidence.quality >= self.KEEP_QUALITY
        )

    def _merge_evidence(
        self,
        state: ResearchState,
        evaluated_results: list[Evidence],
    ) -> list[Evidence]:
        by_url: dict[str, Evidence] = {
            _normalize_url(item.url): item
            for item in state.evidence
            if _normalize_url(item.url)
        }
        kept: list[Evidence] = []

        for evidence in evaluated_results:
            if not self._should_keep(evidence):
                continue

            key = _normalize_url(evidence.url)
            if not key:
                state.evidence.append(evidence)
                kept.append(evidence)
                continue

            existing = by_url.get(key)
            if existing is None:
                state.evidence.append(evidence)
                by_url[key] = evidence
                kept.append(evidence)
                continue

            if (
                evidence.relevance > existing.relevance
                or evidence.quality > existing.quality
            ):
                index = state.evidence.index(existing)
                state.evidence[index] = evidence
                by_url[key] = evidence
                kept.append(evidence)

        return kept

    def _finalize_metrics(self, state: ResearchState) -> None:
        if not state.evidence:
            state.avg_relevance = None
            state.avg_quality = None
            state.useful_evidence_count = 0
            return

        state.avg_relevance = sum(
            item.relevance for item in state.evidence
        ) / len(state.evidence)
        state.avg_quality = sum(
            item.quality for item in state.evidence
        ) / len(state.evidence)
        state.useful_evidence_count = sum(
            1
            for item in state.evidence
            if item.relevance >= self.USEFUL_RELEVANCE
        )

    @staticmethod
    def _record_guard_failure(
        count: int,
        reason: str,
    ) -> tuple[int, str]:
        return count + 1, reason

    def _normalize_query(self, query: str) -> str:
        cleaned = " ".join(query.strip().lower().split())
        return cleaned.replace('"', "").replace("'", "")

    def _query_token_set(self, query: str) -> set[str]:
        return {
            token
            for token in self._normalize_query(query).split()
            if len(token) > 2
        }

    def _query_similarity(self, left: str, right: str) -> float:
        left_tokens = self._query_token_set(left)
        right_tokens = self._query_token_set(right)
        if not left_tokens or not right_tokens:
            return 0.0
        intersection = left_tokens & right_tokens
        union = left_tokens | right_tokens
        return len(intersection) / len(union)

    def _is_duplicate_query(
        self,
        query: str,
        previous_queries: list[str],
    ) -> bool:

        normalized_query = self._normalize_query(query)

        for previous in previous_queries:
            normalized_previous = self._normalize_query(previous)
            if normalized_query == normalized_previous:
                return True
            if (
                self._query_similarity(
                    normalized_query,
                    normalized_previous,
                )
                >= self.NEAR_DUPLICATE_JACCARD
            ):
                return True

        return False
