from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.excon_schemas import (
    Company,
    CompanyProfile,
    Contact,
    ContactProfile,
    DoNotContactEntry,
    Product,
    User,
)


MOCK_DIR = Path(__file__).resolve().parent / "mock"


@dataclass
class MockBundle:
    user: User
    products: list[Product]
    companies: list[Company]
    company_profiles: list[CompanyProfile]
    contacts: list[Contact]
    contact_profiles: list[ContactProfile]
    dnc: list[DoNotContactEntry]

    def product_map(self) -> dict[str, Product]:
        return {product.product_id: product for product in self.products}

    def company_map(self) -> dict[str, Company]:
        return {company.company_id: company for company in self.companies}

    def company_profile_map(self) -> dict[str, CompanyProfile]:
        return {
            profile.company_id: profile for profile in self.company_profiles
        }

    def contact_map(self) -> dict[str, Contact]:
        return {contact.contact_id: contact for contact in self.contacts}

    def contact_profile_map(self) -> dict[str, ContactProfile]:
        return {
            profile.profile_id: profile for profile in self.contact_profiles
        }

    def contacts_for(self, company_id: str) -> list[Contact]:
        return [
            contact
            for contact in self.contacts
            if contact.company_id == company_id
        ]

    def contact_profiles_for(self, company_id: str) -> list[ContactProfile]:
        return [
            profile
            for profile in self.contact_profiles
            if profile.company_id == company_id
        ]

    def products_for(self, profile: CompanyProfile) -> list[Product]:
        product_map = self.product_map()
        return [
            product_map[product_id]
            for product_id in profile.matched_product_ids
            if product_id in product_map
        ]


def load_mock_bundle(mock_dir: Path | None = None) -> MockBundle:
    directory = mock_dir or MOCK_DIR

    user = User.model_validate_json(
        (directory / "user.json").read_text(encoding="utf-8")
    )
    products = [
        Product.model_validate(item)
        for item in _read_json_list(directory / "products.json")
    ]
    companies = [
        Company.model_validate(item)
        for item in _read_json_list(directory / "companies.json")
    ]
    company_profiles = [
        CompanyProfile.model_validate(item)
        for item in _read_json_list(directory / "company_profiles.json")
    ]
    contacts = [
        Contact.model_validate(item)
        for item in _read_json_list(directory / "contacts.json")
    ]
    contact_profiles = [
        ContactProfile.model_validate(item)
        for item in _read_json_list(directory / "contact_profiles.json")
    ]
    dnc = [
        DoNotContactEntry.model_validate(item)
        for item in _read_json_list(directory / "do_not_contact.json")
    ]

    return MockBundle(
        user=user,
        products=products,
        companies=companies,
        company_profiles=company_profiles,
        contacts=contacts,
        contact_profiles=contact_profiles,
        dnc=dnc,
    )


def _read_json_list(path: Path) -> list[dict]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return payload
