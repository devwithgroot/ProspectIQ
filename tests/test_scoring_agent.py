from agents.state import ResearchState
from agents.research_agent import ResearchAgent
from agents.scoring_agent import ScoringAgent


def main():
    state = ResearchState(
        company_name="Asian Paints",
        research_goal=(
            "Determine whether Asian Paints is a high-value "
            "sales prospect."
        ),
        max_steps=3,
    )

    research_agent = ResearchAgent()

    print("\n==============================")
    print("STARTING RESEARCH")
    print("==============================")

    state = research_agent.run(state)

    print("\n==============================")
    print("STARTING SCORING")
    print("==============================")

    scoring_agent = ScoringAgent()

    score = scoring_agent.score(state)

    print("\n==============================")
    print("PROSPECT SCORE")
    print("==============================")

    print(
        score.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()