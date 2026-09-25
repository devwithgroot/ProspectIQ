from agents.state import ResearchState
from agents.research_agent import ResearchAgent
from agents.scoring_agent import ScoringAgent
from agents.report_agent import ReportAgent


def main():
    state = ResearchState(
        company_name="Asian Paints",
        research_goal=(
            "Determine whether Asian Paints is a high-value "
            "sales prospect."
        ),
        max_steps=3,
    )

    # ------------------------------
    # RESEARCH
    # ------------------------------

    research_agent = ResearchAgent()

    print("\n==============================")
    print("STARTING RESEARCH")
    print("==============================")

    state = research_agent.run(state)

    # ------------------------------
    # SCORING
    # ------------------------------

    scoring_agent = ScoringAgent()

    print("\n==============================")
    print("STARTING SCORING")
    print("==============================")

    score = scoring_agent.score(state)

    print("\nProspect Score:")
    print(score.model_dump_json(indent=2))

    # ------------------------------
    # REPORT
    # ------------------------------

    report_agent = ReportAgent()

    print("\n==============================")
    print("STARTING REPORT GENERATION")
    print("==============================")

    report = report_agent.generate(
        state=state,
        score=score,
    )

    print("\n==============================")
    print("PROSPECTIQ REPORT")
    print("==============================")

    print(
        report.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()