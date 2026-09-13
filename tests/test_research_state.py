from agents.state import ResearchState


def main():
    state = ResearchState(
        company_name="Asian Paints",
        research_goal=(
            "Determine whether Asian Paints is a high-value "
            "sales prospect."
        ),
    )

    print(state.model_dump_json(indent=2))


if __name__ == "__main__":
    main()