from tools.people_enrichment import PeopleEnrichmentTool


def main():
    tool = PeopleEnrichmentTool()

    person_id = input("Enter Prospeo person_id: ").strip()

    person = tool.execute(
        person_id=person_id,
        enrich_mobile=True,
    )

    print("\n========== ENRICHED PERSON ==========")

    print(f"ID: {person.id}")
    print(f"Name: {person.name}")
    print(f"Title: {person.title}")
    print(f"Company: {person.organization_name}")

    print(f"\nEmail: {person.email}")
    print(f"Email Status: {person.email_status}")

    print(f"Mobile: {person.mobile}")
    print(f"Mobile Status: {person.mobile_status}")

    print(f"\nLinkedIn: {person.linkedin_url}")

    print(f"\nLocation:")
    print(f"  City: {person.city}")
    print(f"  State: {person.state}")
    print(f"  Country: {person.country}")


if __name__ == "__main__":
    main()