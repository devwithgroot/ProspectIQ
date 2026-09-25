from pathlib import Path

from app.prospect_upload import load_prospect_csv


def main():
    print("\n==============================")
    print("PROSPECT UPLOAD TEST")
    print("==============================")

    sample = Path("data/uploads/sample_prospects.csv")
    rows = load_prospect_csv(sample)

    assert len(rows) == 2
    assert rows[0].company_name == "Asian Paints"
    assert rows[0].website == "https://www.asianpaints.com"
    assert rows[1].company_name == "Havells India"
    print(f"loaded {len(rows)} companies from {sample}")

    try:
        load_prospect_csv("data/uploads/does_not_exist.csv")
        raise AssertionError("missing file should fail")
    except FileNotFoundError:
        print("missing file blocked")

    print("PROSPECT UPLOAD TEST PASSED")


if __name__ == "__main__":
    main()
