from app.people_mapper import person_to_contact
from config.schemas import PersonData


def main():
    print("\n==============================")
    print("PEOPLE MAPPER TEST")
    print("==============================")

    person = PersonData(
        id="abc123",
        first_name="Amit",
        last_name="Sharma",
        title="Vice President, Supply Chain",
        linkedin_url="https://www.linkedin.com/in/amit-sharma",
        departments=["Supply Chain"],
        seniority="vp",
    )
    contact = person_to_contact(person, "co_asian_paints")
    assert contact is not None
    assert contact.company_id == "co_asian_paints"
    assert contact.full_name == "Amit Sharma"
    assert contact.decision_role == "economic_buyer"
    assert contact.preferred_channel == "linkedin"
    assert contact.consent.linkedin is True
    assert contact.consent.email is False
    print(f"{contact.full_name} → {contact.decision_role}")

    founder = person_to_contact(
        PersonData(
            first_name="Pablo",
            last_name="Salerno",
            title="Fundador",
        ),
        "co_unimad",
    )
    assert founder is not None
    assert founder.title == "Founder"
    assert founder.decision_role == "economic_buyer"
    print(f"{founder.full_name} · {founder.title} → {founder.decision_role}")

    unnamed = person_to_contact(PersonData(title="Analyst"), "co_x")
    assert unnamed is None
    print("blank name is skipped")

    print("\nPEOPLE MAPPER TEST PASSED")


if __name__ == "__main__":
    main()
