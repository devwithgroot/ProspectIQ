from tools.people_data import PeopleDataTool


def main():

    print("=" * 60)
    print("PROSPECTIQ PEOPLE DISCOVERY TEST")
    print("=" * 60)

    company = input(
        "\nEnter company name: "
    ).strip()

    tool = PeopleDataTool()

    print(
        f"\nSearching for people at "
        f"{company}..."
    )

    result = tool.execute(
        company=company,
        limit=10,
    )

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)

    print(
        f"\nStatus: {result.status}"
    )

    print(
        f"Searched company: "
        f"{result.searched_company}"
    )

    if result.resolved_company:

        print(
            f"Resolved company: "
            f"{result.resolved_company}"
        )

    if result.domain:

        print(
            f"Domain: {result.domain}"
        )

    # =========================================================
    # COMPANY SUGGESTIONS
    # =========================================================

    if result.suggested_companies:

        print(
            "\nPossible company matches:"
        )

        for index, company in enumerate(
            result.suggested_companies,
            start=1,
        ):

            print(
                f"\n{index}. {company.name}"
            )

            if company.domain:

                print(
                    f"   Domain: "
                    f"{company.domain}"
                )

            if company.description:

                print(
                    f"   Description: "
                    f"{company.description}"
                )

            if company.source_url:

                print(
                    f"   Source: "
                    f"{company.source_url}"
                )

    # =========================================================
    # PEOPLE
    # =========================================================

    if result.people:

        print(
            f"\nUnique people found: "
            f"{len(result.people)}"
        )

        for index, person in enumerate(
            result.people,
            start=1,
        ):

            print("\n" + "-" * 60)

            print(
                f"PERSON {index}"
            )

            print(
                f"Name       : "
                f"{person.name}"
            )

            print(
                f"Title      : "
                f"{person.title or 'N/A'}"
            )

            print(
                f"Company    : "
                f"{person.company or 'N/A'}"
            )

            print(
                f"Location   : "
                f"{person.location or 'N/A'}"
            )

            print(
                f"Email      : "
                f"{person.email or 'N/A'}"
            )

            print(
                f"Mobile     : "
                f"{person.mobile or 'N/A'}"
            )

            if person.prospeo_verified:

                print(
                    "Prospeo    : MATCHED"
                )

            else:

                print(
                    "Prospeo    : NO MATCH"
                )

            print(
                f"Sources    : "
                f"{', '.join(person.data_sources)}"
            )

            print(
                f"Confidence : "
                f"{person.confidence or 'N/A'}"
            )

            if person.source_type:

                print(
                    f"Source Type: "
                    f"{person.source_type}"
                )

            if person.source_url:

                print(
                    f"Web Source : "
                    f"{person.source_url}"
                )

            if person.evidence:

                print(
                    "\nEvidence:"
                )

                print(
                    person.evidence[:1000]
                )

    # =========================================================
    # MESSAGE
    # =========================================================

    if result.message:

        print(
            "\n" + "=" * 60
        )

        print(
            result.message
        )


if __name__ == "__main__":
    main()