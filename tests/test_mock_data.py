from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("MOCK DATA JOIN TEST")
    print("==============================")

    bundle = load_mock_bundle()

    product_ids = {product.product_id for product in bundle.products}
    company_ids = {company.company_id for company in bundle.companies}
    contact_ids = {contact.contact_id for contact in bundle.contacts}

    assert bundle.user.user_id == "us_priya_mehta"
    assert set(bundle.user.product_ids) <= product_ids

    for product_id in bundle.user.product_ids:
        assert product_id in product_ids, product_id

    for profile in bundle.company_profiles:
        assert profile.company_id in company_ids, profile.profile_id
        for product_id in profile.matched_product_ids:
            assert product_id in product_ids, (
                f"{profile.company_id} references missing {product_id}"
            )

    for contact in bundle.contacts:
        assert contact.company_id in company_ids, contact.contact_id

    for profile in bundle.contact_profiles:
        assert profile.contact_id in contact_ids, profile.profile_id
        assert profile.company_id in company_ids, profile.profile_id

        contact = bundle.contact_map()[profile.contact_id]
        assert contact.company_id == profile.company_id, profile.profile_id

    assert len(bundle.contact_profiles) == len(bundle.contacts)

    dnc_contact_ids = {
        entry.value
        for entry in bundle.dnc
        if entry.kind == "contact_id"
    }
    assert "ct_ap_004" in dnc_contact_ids
    assert bundle.contact_map()["ct_ap_004"].do_not_contact is True
    assert bundle.contact_map()["ct_ap_003"].email is None
    assert bundle.contact_map()["ct_ap_002"].consent.sms is False

    print(f"user: {bundle.user.full_name} @ {bundle.user.company.name}")
    print(f"products: {len(bundle.products)}")
    print(f"companies: {len(bundle.companies)}")
    print(f"company profiles: {len(bundle.company_profiles)}")
    print(f"contacts: {len(bundle.contacts)}")
    print(f"contact profiles: {len(bundle.contact_profiles)}")
    print(f"dnc entries: {len(bundle.dnc)}")
    print("\nMOCK DATA JOIN TEST PASSED")


if __name__ == "__main__":
    main()
