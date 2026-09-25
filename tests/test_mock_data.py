from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("MOCK DATA JOIN TEST")
    print("==============================")

    bundle = load_mock_bundle()

    product_ids = {product.product_id for product in bundle.products}
    prospect_ids = {prospect.prospect_id for prospect in bundle.prospects}
    contact_ids = {contact.contact_id for contact in bundle.contacts}

    assert bundle.user.user_id == "us_priya_mehta"
    assert set(bundle.user.product_ids) <= product_ids

    for product_id in bundle.user.product_ids:
        assert product_id in product_ids, product_id

    for prospect in bundle.prospects:
        for product_id in prospect.matched_product_ids:
            assert product_id in product_ids, (
                f"{prospect.prospect_id} references missing {product_id}"
            )

    for contact in bundle.contacts:
        assert contact.prospect_id in prospect_ids, contact.contact_id

    for profile in bundle.profiles:
        assert profile.contact_id in contact_ids, profile.profile_id
        assert profile.prospect_id in prospect_ids, profile.profile_id

        contact = bundle.contact_map()[profile.contact_id]
        assert contact.prospect_id == profile.prospect_id, profile.profile_id

    assert len(bundle.profiles) == len(bundle.contacts)

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
    print(f"prospects: {len(bundle.prospects)}")
    print(f"contacts: {len(bundle.contacts)}")
    print(f"profiles: {len(bundle.profiles)}")
    print(f"dnc entries: {len(bundle.dnc)}")
    print("\nMOCK DATA JOIN TEST PASSED")


if __name__ == "__main__":
    main()
