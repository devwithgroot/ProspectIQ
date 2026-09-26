import re

from config.schemas import Evidence

_WORD_RE = re.compile(r"[a-z0-9]+")

_SIGNAL_TERMS = (
    "growth",
    "expand",
    "expansion",
    "hiring",
    "workforce",
    "funding",
    "investment",
    "acquisition",
    "merger",
    "technology",
    "digital",
    "transform",
    "strategic",
    "initiative",
    "partnership",
    "revenue",
    "market",
    "leadership",
    "executive",
    "ceo",
    "cfo",
    "cto",
)

_SIGNAL_TERM_GROUPS = (
    ("expand", "expansion"),
)

_GROUPED_TERMS = {
    term
    for group in _SIGNAL_TERM_GROUPS
    for term in group
}

_BOUNDARY_CACHE: dict[str, re.Pattern[str]] = {}


def _signal_term_pattern(term: str) -> re.Pattern[str]:
    cached = _BOUNDARY_CACHE.get(term)
    if cached is None:
        cached = re.compile(rf"\b{re.escape(term)}\b")
        _BOUNDARY_CACHE[term] = cached
    return cached


def _signal_term_matches(text: str, term: str) -> bool:
    return _signal_term_pattern(term).search(text) is not None


class EvidenceEvaluator:
    def evaluate(
        self,
        evidence: Evidence,
        research_goal: str,
        *,
        company_name: str | None = None,
        company_domain: str | None = None,
    ) -> Evidence:

        combined = f"{evidence.title} {evidence.content}".lower()

        signal_score = self._calculate_signal_relevance(combined)
        goal_score = self._calculate_goal_relevance(
            combined,
            research_goal,
        )

        relevance = 0.7 * signal_score + 0.3 * goal_score

        if company_name and company_name.lower() in combined:
            relevance = min(relevance + 0.1, 1.0)

        quality = self._calculate_quality(
            evidence,
            company_domain=company_domain,
        )

        evidence.relevance = min(relevance, 1.0)
        evidence.quality = quality

        return evidence

    def _calculate_signal_relevance(self, text: str) -> float:
        match_count = 0

        for group in _SIGNAL_TERM_GROUPS:
            if any(_signal_term_matches(text, term) for term in group):
                match_count += 1

        for term in _SIGNAL_TERMS:
            if term in _GROUPED_TERMS:
                continue
            if _signal_term_matches(text, term):
                match_count += 1

        if match_count == 0:
            return 0.0
        return min(match_count / 4.0, 1.0)

    def _calculate_goal_relevance(
        self,
        content: str,
        research_goal: str,
    ) -> float:

        goal_words = {
            token
            for token in _WORD_RE.findall(research_goal.lower())
            if len(token) > 4
        }

        if not goal_words:
            return 0.0

        matches = sum(
            1
            for word in goal_words
            if word in content
        )

        score = matches / len(goal_words)

        return min(score, 1.0)

    def _calculate_quality(
        self,
        evidence: Evidence,
        *,
        company_domain: str | None = None,
    ) -> float:

        url = evidence.url.lower()

        if company_domain:
            domain = company_domain.lower().strip().lstrip(".")
            if domain and domain in url:
                return 1.0

        high_quality_domains = (
            ".gov",
            ".edu",
            "reuters.com",
            "bloomberg.com",
            "forbes.com",
            "wsj.com",
            "ft.com",
        )

        if any(
            domain in url
            for domain in high_quality_domains
        ):
            return 0.9

        if evidence.content and len(evidence.content.strip()) > 120:
            return 0.65

        if evidence.content:
            return 0.5

        return 0.2
