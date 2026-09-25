from pathlib import Path
import tempfile

from app.prospect_upload import (
    MAX_UPLOAD_BYTES,
    load_prospect_csv,
    preview_prospect_csv,
    upload_too_large,
)


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

    for path in sorted(Path("data/uploads").glob("sample_*.csv")):
        if path == sample:
            continue
        loaded = load_prospect_csv(path)
        assert loaded
        print(f"loaded {len(loaded)} companies from {path}")

    names_only = load_prospect_csv("data/uploads/sample_names_only.csv")
    assert all(row.website is None and row.notes is None for row in names_only)

    mixed = load_prospect_csv("data/uploads/sample_mixed.csv")
    names = [row.company_name for row in mixed]
    assert names.count("Hindalco") == 1
    assert mixed[0].website is None

    try:
        load_prospect_csv("data/uploads/does_not_exist.csv")
        raise AssertionError("missing file should fail")
    except FileNotFoundError:
        print("missing file blocked")

    oversized = Path(tempfile.gettempdir()) / "prospectiq_oversized.csv"
    oversized.write_bytes(b"x" * (MAX_UPLOAD_BYTES + 1))
    try:
        load_prospect_csv(oversized)
        raise AssertionError("oversized file should fail")
    except ValueError as exc:
        assert "5 MB" in str(exc)
        print("oversized file blocked")

    assert upload_too_large(None) is False
    assert upload_too_large(MAX_UPLOAD_BYTES) is False
    assert upload_too_large(MAX_UPLOAD_BYTES + 1) is True
    print("5 MB per-file limit ok")

    rows = preview_prospect_csv(sample)
    assert [row["company_name"] for row in rows] == [
        "Asian Paints",
        "Havells India",
    ]
    print("CSV preview ok")

    print("PROSPECT UPLOAD TEST PASSED")


if __name__ == "__main__":
    main()
