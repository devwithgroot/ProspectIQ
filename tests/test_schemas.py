from config.schemas import ProspectAnalysis, Signal


def main():
    analysis = ProspectAnalysis(
        company_name="Example Industries",
        industry="Manufacturing",
        company_summary="A growing manufacturing company.",
        signals=[
            Signal(
                type="expansion",
                description="The company is expanding operations.",
                strength="high",
                evidence="Opened two new facilities.",
            )
        ],
        pain_points=[
            "Distributed sales operations",
            "Manual reporting",
        ],
        prospect_score=82,
        confidence=0.87,
        recommendation="Prioritize for sales outreach.",
    )

    print(analysis.model_dump_json(indent=2))


if __name__ == "__main__":
    main()