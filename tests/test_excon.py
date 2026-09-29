from app.excon import Excon
from connectors.base import ConnectorError
from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("EXCON ORCHESTRATOR TEST")
    print("==============================")

    bundle = load_mock_bundle()
    company = bundle.company_map()["pr_asian_paints"]
    company_profile = bundle.company_profile_map()[company.company_id]
    contacts = bundle.contacts_for(company.company_id)
    profiles = bundle.contact_profiles_for(company.company_id)
    products = bundle.products_for(company_profile)

    excon = Excon(dry_run=True, dnc=bundle.dnc)

    batch = excon.prepare(
        user=bundle.user,
        company=company,
        company_profile=company_profile,
        profiles=profiles,
        contacts=contacts,
        products=products,
    )

    skipped = {
        package.contact_id: package.skipped_reason
        for package in batch.packages
        if package.skipped_reason
    }
    drafted = [
        draft
        for package in batch.packages
        for draft in package.drafts
    ]

    print(f"packages: {len(batch.packages)}")
    print(f"drafts: {len(drafted)}")
    print(f"skipped: {skipped}")

    for draft in drafted:
        print(f"\n--- {draft.contact_id} / {draft.channel} ---")
        if draft.subject:
            print(f"Subject: {draft.subject}")
        print(draft.body)

    assert "ct_ap_004" in skipped
    assert len(drafted) >= 3

    first = drafted[0]
    try:
        excon.send(first.draft_id)
        raise AssertionError("Unapproved send should fail")
    except ConnectorError as exc:
        print(f"\nunapproved send blocked: {exc}")

    edited = excon.edit(
        first.draft_id,
        body=first.body + "\n\nEdited by salesperson.",
    )
    assert edited.status == "draft"
    assert "Edited by salesperson" in edited.body

    approved = excon.approve(first.draft_id)
    assert approved.status == "approved"

    result = excon.send(first.draft_id)
    assert result.success is True
    assert result.dry_run is True
    assert excon.drafts[first.draft_id].status == "sent"
    print(f"dry-run send ok: {result.external_id}")

    event_types = [event.event_type for event in excon.events]
    assert "drafted" in event_types
    assert "edited" in event_types
    assert "approved" in event_types
    assert "sent" in event_types
    assert "send_failed" in event_types
    print(f"events: {event_types}")

    print("\nEXCON ORCHESTRATOR TEST PASSED")


if __name__ == "__main__":
    main()
