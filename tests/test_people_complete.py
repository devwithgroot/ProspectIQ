from tools.people_data import PeopleDataTool
from tools.people_enrichment import PeopleEnrichmentTool


def main():
    company_name = input("Enter company name: ").strip()

    if not company_name:
        print("Company name is required.")
        return

    people_tool = PeopleDataTool()
    enrichment_tool = PeopleEnrichmentTool()

    print(f"\nSearching people at: {company_name}...")

    people = people_tool.execute(
        company=company_name,
        limit=5,
    )

    if not people:
        print("No people found.")
        return

    print(f"Found {len(people)} people.")

    # IMPORTANT:
    # For now, enrich only ONE person so we don't
    # unnecessarily hit Prospeo rate limits/credits.
    person = people[0]

    print("\nEnriching first person...")
    print(f"Person: {person.name}")
    print(f"Person ID: {person.id}")

    try:
        enriched_person = enrichment_tool.execute(
            person_id=person.id,
            enrich_mobile=True,
        )

        print("\n" + "=" * 70)
        print("ENRICHED PERSON")
        print("=" * 70)

        print(f"Name           : {enriched_person.name}")
        print(f"Title          : {enriched_person.title}")
        print(f"Company        : {enriched_person.organization_name}")

        print(f"\nEmail          : {enriched_person.email}")
        print(f"Email Status   : {enriched_person.email_status}")

        print(f"Mobile         : {enriched_person.mobile}")
        print(f"Mobile Status  : {enriched_person.mobile_status}")

        print(f"\nLinkedIn       : {enriched_person.linkedin_url}")

        print(
            f"Location       : "
            f"{enriched_person.city}, "
            f"{enriched_person.state}, "
            f"{enriched_person.country}"
        )

        print(f"Seniority      : {enriched_person.seniority}")
        print(f"Departments    : {enriched_person.departments}")
        print(f"Person ID      : {enriched_person.id}")

        print("=" * 70)

    except Exception as exc:
        print(f"\nEnrichment failed: {exc}")

    print("\nDone.")


if __name__ == "__main__":
    main()