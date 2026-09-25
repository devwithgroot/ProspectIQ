from tools.providers.apollo import ApolloProvider


def main():

    print("=" * 60)
    print("APOLLO PEOPLE SEARCH TEST")
    print("=" * 60)

    provider = ApolloProvider()

    print("\nSearching for decision makers...\n")

    people = provider.search_people(
        company_name="Asian Paints",
        titles=[
            "Chief Technology Officer",
            "Chief Information Officer",
            "VP Engineering",
            "Head of Technology",
        ],
        limit=10,
    )

    print(f"Found: {len(people)} people")

    print("\n" + "-" * 60)

    for index, person in enumerate(
        people,
        start=1,
    ):

        print(f"\nPerson {index}")

        print(f"Name: {person.name}")
        print(f"Title: {person.title}")
        print(f"LinkedIn: {person.linkedin_url}")
        print(
            f"Organization: "
            f"{person.organization_name}"
        )
        print(f"Location: {person.city}, {person.country}")
        print(f"Seniority: {person.seniority}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()