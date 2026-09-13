from config.schemas import Evidence
from tools.evidence_evaluator import EvidenceEvaluator


def main():
    evidence = Evidence(
        title="Asian Paints announces expansion",
        url="https://www.asianpaints.com/about-us.html",
        content=(
            "Asian Paints is expanding its manufacturing "
            "capacity in India through new investments."
        ),
        source="Tavily",
        evidence_type="web",
    )

    evaluator = EvidenceEvaluator()

    evaluated = evaluator.evaluate(
        evidence=evidence,
        research_goal=(
            "Determine whether Asian Paints "
            "is a high-value sales prospect."
        ),
    )

    print("\n--- Evaluated Evidence ---")
    print(f"Title: {evaluated.title}")
    print(f"Relevance: {evaluated.relevance}")
    print(f"Quality: {evaluated.quality}")


if __name__ == "__main__":
    main()