from pathlib import Path

from config.catalog import (
    Industry,
    SellerTitle,
    catalog_error,
    catalog_payload,
    parse_industry,
    parse_title,
    title_allowed,
    titles_for,
)
from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("CATALOG ENUM TEST")
    print("==============================")

    root = Path(__file__).resolve().parents[1]
    assert (root / "config/catalog.json").read_text(
        encoding="utf-8"
    ) == (root / "web/lib/catalog-data.json").read_text(encoding="utf-8")
    print("frontend catalog copy matches config/catalog.json")

    labels = [title.value for title in SellerTitle]
    assert len(labels) == len(set(labels)), "title labels must be unique"
    assert len(list(Industry)) >= 20
    print(f"{len(list(Industry))} industries, {len(list(SellerTitle))} titles")

    payload = catalog_payload()
    assert payload["industries"]
    software = parse_industry("Software / SaaS")
    assert software is Industry.software_saas
    assert parse_industry("software_saas") is software

    ae = parse_title("Account Executive")
    assert ae is SellerTitle.account_executive
    assert title_allowed(ae, software)
    assert title_allowed(ae, parse_industry("Industrial software"))
    print("common sales titles are available across industries")

    plant = parse_title("Plant Head")
    assert title_allowed(plant, parse_industry("Manufacturing"))
    assert not title_allowed(plant, software)
    assert catalog_error("Plant Head", "Software / SaaS")
    assert catalog_error("Wizard of Sales", "Software / SaaS")
    assert catalog_error("Account Executive", "Not an industry")
    assert catalog_error("Account Executive", "Software / SaaS") is None
    print("industry-specific titles are rejected outside that industry")

    pharma_titles = {title.value for title in titles_for(parse_industry("pharma"))}
    assert "Medical Representative" in pharma_titles
    assert "Medical Science Liaison" in pharma_titles
    banking_titles = {title.value for title in titles_for(parse_industry("banking"))}
    assert "Relationship Manager" in banking_titles
    fmcg_titles = {title.value for title in titles_for(parse_industry("FMCG"))}
    assert "Area Sales Manager" in fmcg_titles
    print("pharma, banking, and FMCG title sets look right")

    user = load_mock_bundle().user
    assert user.title is SellerTitle.account_executive
    assert user.company.industry is Industry.industrial_software
    print("mock seller uses catalog enums")

    print("\nCATALOG ENUM TEST PASSED")


if __name__ == "__main__":
    main()
