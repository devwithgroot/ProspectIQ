from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from config.excon_schemas import (
    Contact,
    ContactProfile,
    DoNotContactEntry,
    Product,
    Prospect,
    User,
)


MOCK_DIR = Path(__file__).resolve().parent / "mock"


@dataclass
class MockBundle:
    user: User
    products: list[Product]
    prospects: list[Prospect]
    contacts: list[Contact]
    profiles: list[ContactProfile]
    dnc: list[DoNotContactEntry]

    def product_map(self) -> dict[str, Product]:
        return {product.product_id: product for product in self.products}

    def prospect_map(self) -> dict[str, Prospect]:
        return {prospect.prospect_id: prospect for prospect in self.prospects}

    def contact_map(self) -> dict[str, Contact]:
        return {contact.contact_id: contact for contact in self.contacts}

    def profile_map(self) -> dict[str, ContactProfile]:
        return {profile.profile_id: profile for profile in self.profiles}

    def contacts_for(self, prospect_id: str) -> list[Contact]:
        return [
            contact
            for contact in self.contacts
            if contact.prospect_id == prospect_id
        ]

    def profiles_for(self, prospect_id: str) -> list[ContactProfile]:
        return [
            profile
            for profile in self.profiles
            if profile.prospect_id == prospect_id
        ]

    def products_for(self, prospect: Prospect) -> list[Product]:
        product_map = self.product_map()
        return [
            product_map[product_id]
            for product_id in prospect.matched_product_ids
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
    prospects = [
        Prospect.model_validate(item)
        for item in _read_json_list(directory / "prospects.json")
    ]
    contacts = [
        Contact.model_validate(item)
        for item in _read_json_list(directory / "contacts.json")
    ]
    profiles = [
        ContactProfile.model_validate(item)
        for item in _read_json_list(directory / "profiles.json")
    ]
    dnc = [
        DoNotContactEntry.model_validate(item)
        for item in _read_json_list(directory / "do_not_contact.json")
    ]

    return MockBundle(
        user=user,
        products=products,
        prospects=prospects,
        contacts=contacts,
        profiles=profiles,
        dnc=dnc,
    )


def _read_json_list(path: Path) -> list[dict]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return payload
