from agents.outreach_agent import OutreachAgent
from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("OUTREACH AGENT TEST")
    print("==============================")

    bundle = load_mock_bundle()
    company = bundle.company_map()["pr_asian_paints"]
    company_profile = bundle.company_profile_map()[company.company_id]
    products = bundle.products_for(company_profile)
    agent = OutreachAgent()

    amit = bundle.contact_map()["ct_ap_001"]
    amit_profile = bundle.contact_profile_map()["pf_ap_001"]
    amit_package = agent.prepare_package(
        user=bundle.user,
        products=products,
        company=company,
        company_profile=company_profile,
        contact=amit,
        profile=amit_profile,
        dnc=bundle.dnc,
    )
    assert amit_package.skipped_reason is None
    assert len(amit_package.drafts) == 1
    assert amit_package.drafts[0].channel == "email"
    assert amit_package.drafts[0].is_primary is True
    print(f"\nAmit primary channel: {amit_package.drafts[0].channel}")
    print(f"Subject: {amit_package.drafts[0].subject}")
    print(amit_package.drafts[0].body)

    kavita = bundle.contact_map()["ct_ap_002"]
    kavita_profile = bundle.contact_profile_map()["pf_ap_002"]
    kavita_package = agent.prepare_package(
        user=bundle.user,
        products=products,
        company=company,
        company_profile=company_profile,
        contact=kavita,
        profile=kavita_profile,
        dnc=bundle.dnc,
    )
    assert kavita_package.drafts[0].channel == "linkedin"
    print(f"\nKavita primary channel: {kavita_package.drafts[0].channel}")
    print(kavita_package.drafts[0].body)

    deepak = bundle.contact_map()["ct_ap_004"]
    deepak_profile = bundle.contact_profile_map()["pf_ap_004"]
    deepak_package = agent.prepare_package(
        user=bundle.user,
        products=products,
        company=company,
        company_profile=company_profile,
        contact=deepak,
        profile=deepak_profile,
        dnc=bundle.dnc,
    )
    assert deepak_package.drafts == []
    assert "do-not-contact" in (deepak_package.skipped_reason or "")
    print(f"\nDeepak skipped: {deepak_package.skipped_reason}")

    print("\nOUTREACH AGENT TEST PASSED")


if __name__ == "__main__":
    main()
