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
        matches = sum(
            1
            for term in _SIGNAL_TERMS
            if term in text
        )
        if matches == 0:
            return 0.0
        return min(matches / 4.0, 1.0)

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
