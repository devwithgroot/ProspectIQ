from app.orchestrator import ProspectIQ


def main():
    print("\n==============================")
    print("PROSPECTIQ ORCHESTRATOR TEST")
    print("==============================")

    app = ProspectIQ()

    print("\nStarting full analysis...")

    report = app.analyze(
        company_name="Asian Paints",
        research_goal=(
            "Determine whether Asian Paints is a high-value "
            "B2B sales prospect."
        ),
    )

    print("\n==============================")
    print("ANALYSIS COMPLETE")
    print("==============================")

    print(
        report.model_dump_json(indent=2)
    )


if __name__ == "__main__":
    main()