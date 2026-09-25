import json
from pathlib import Path

from app.onboarding import reuse_seller, same_website
from config.excon_schemas import User
from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("REUSE SELLER COMPANY TEST")
    print("==============================")

    assert same_website("https://www.tezbytes.dev", "tezbytes.dev")
    assert not same_website("https://tezbytes.dev", "https://other.dev")
    print("website match ok")

    bundle = load_mock_bundle()
    user = bundle.user
    products = bundle.products
    updated, kept = reuse_seller(
        user,
        products,
        full_name="Anish Srivastava",
        phone="+919845512210",
        email=user.email,
        outreach_email=user.email,
        website=user.company.website,
        title=user.title,
        industry=user.company.industry,
    )
    assert kept == products
    assert updated.company.name == user.company.name
    assert updated.company.description == user.company.description
    assert updated.full_name == "Anish Srivastava"
    print(f"reused {updated.company.name} with {len(kept)} products")

    raw = json.loads(Path("data/mock/user.json").read_text(encoding="utf-8"))
    User.model_validate(raw)
    print("saved user still validates")

    print("\nREUSE SELLER COMPANY TEST PASSED")


if __name__ == "__main__":
    main()
