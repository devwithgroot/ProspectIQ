from config.schemas import Evidence


class EvidenceEvaluator:
    def evaluate(
        self,
        evidence: Evidence,
        research_goal: str,
    ) -> Evidence:

        content = evidence.content.lower()

        relevance = self._calculate_relevance(
            content,
            research_goal,
        )

        quality = self._calculate_quality(
            evidence,
        )

        evidence.relevance = relevance
        evidence.quality = quality

        return evidence

    def _calculate_relevance(
        self,
        content: str,
        research_goal: str,
    ) -> float:

        goal_words = {
            word.lower()
            for word in research_goal.split()
            if len(word) > 4
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
    ) -> float:

        url = evidence.url.lower()

        high_quality_domains = (
            ".gov",
            ".edu",
            "reuters.com",
            "bloomberg.com",
            "forbes.com",
        )

        company_source = (
            "asianpaints.com"
            in url
        )

        if company_source:
            return 1.0

        if any(
            domain in url
            for domain in high_quality_domains
        ):
            return 0.9

        if evidence.content:
            return 0.6

        return 0.2