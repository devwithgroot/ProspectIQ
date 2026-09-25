from __future__ import annotations

from typing import Any

from app.excon import Excon
from config.excon_schemas import (
    Company,
    CompanyProfile,
    Contact,
    ContactProfile,
    Product,
    User,
)


def draft_for_contact(payload: dict[str, Any], contact_id: str) -> dict[str, Any]:
    user = User.model_validate(payload["user"])
    products = [
        Product.model_validate(item) for item in payload.get("products") or []
    ]
    companies = [
        Company.model_validate(item) for item in payload.get("companies") or []
    ]
    company_profiles = [
        CompanyProfile.model_validate(item)
        for item in payload.get("company_profiles") or []
    ]
    contacts = [
        Contact.model_validate(item) for item in payload.get("contacts") or []
    ]
    contact_profiles = [
        ContactProfile.model_validate(item)
        for item in payload.get("contact_profiles") or []
    ]

    contact = next(
        (item for item in contacts if item.contact_id == contact_id),
        None,
    )
    if contact is None:
        raise ValueError("That person is not in this research run.")

    company = next(
        (item for item in companies if item.company_id == contact.company_id),
        None,
    )
    company_profile = next(
        (
            item
            for item in company_profiles
            if item.company_id == contact.company_id
        ),
        None,
    )
    contact_profile = next(
        (item for item in contact_profiles if item.contact_id == contact_id),
        None,
    )
    if company is None or company_profile is None or contact_profile is None:
        raise ValueError("Missing company or contact briefing for that person.")

    matched = [
        product
        for product in products
        if product.product_id in company_profile.matched_product_ids
    ] or products

    batch = Excon(dry_run=True).prepare(
        user=user,
        company=company,
        company_profile=company_profile,
        profiles=[contact_profile],
        contacts=[contact],
        products=matched,
    )
    package = batch.packages[0] if batch.packages else None
    drafts = package.drafts if package else []
    return {
        "batch_id": batch.batch_id,
        "company_id": company.company_id,
        "contact_id": contact.contact_id,
        "contact_name": contact.full_name,
        "skipped_reason": package.skipped_reason if package else "No draft.",
        "drafts": [draft.model_dump(mode="json") for draft in drafts],
        "dry_run": True,
    }
