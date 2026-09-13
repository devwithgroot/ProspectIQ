from agents.research_agent import ResearchAgent
from agents.state import ResearchState


def main():
    state = ResearchState(
        company_name="Asian Paints",
        research_goal=(
            "Determine whether Asian Paints is a high-value "
            "sales prospect."
        ),
        max_steps=4,
    )

    agent = ResearchAgent()

    final_state = agent.run(state)

    print("\n==============================")
    print("RESEARCH COMPLETE")
    print("==============================")

    print(f"\nCompany: {final_state.company_name}")
    print(f"Steps taken: {final_state.steps_taken}")

    print("\nQueries:")
    for query in final_state.queries:
        print(f"- {query}")

    print(
        f"\nEvidence collected: "
        f"{len(final_state.evidence)}"
    )

    for index, evidence in enumerate(
        final_state.evidence,
        start=1,
    ):
        print(f"\n--- Evidence {index} ---")
        print(f"Title: {evidence.title}")
        print(f"URL: {evidence.url}")
        print(f"Source: {evidence.source}")
        print(f"Type: {evidence.evidence_type}")
        print(f"Content: {evidence.content[:300]}...")
        print(f"Relevance: {evidence.relevance}")
        print(f"Quality: {evidence.quality}")


if __name__ == "__main__":
    main()