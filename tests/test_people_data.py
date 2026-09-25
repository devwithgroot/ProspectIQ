from tools.people_data import PeopleDataTool


def main():

    print("=" * 60)
    print("PROSPEO PEOPLE SEARCH TEST")
    print("=" * 60)

    tool = PeopleDataTool()

    print(f"\nName: {tool.name}")
    print(f"Description: {tool.description}")

    print("\nSearching for people at Asian Paints...\n")

    people = tool.execute(
        company="Asian Paints",
        limit=5,
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
        print(f"Company: {person.organization_name}")
        print(f"LinkedIn: {person.linkedin_url}")
        print(f"Location: {person.city}, {person.country}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()