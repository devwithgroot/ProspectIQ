from config.schemas import ResearchDecision


def main():
    decision = ResearchDecision(
        action="search",
        query="Asian Paints recent expansion 2026",
        reasoning="We need recent growth signals.",
    )

    print(decision.model_dump_json(indent=2))


if __name__ == "__main__":
    main()