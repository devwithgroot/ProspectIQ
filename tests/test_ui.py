import importlib
import sys
import tempfile
from pathlib import Path

from app.prospect_upload import MAX_UPLOAD_BYTES
from app.ui_logic import (
    invalid_catalog_selection,
    invalid_email_fields,
    missing_required_fields,
    normalize_url,
    preview_prospect_csv,
    upload_too_large,
)


def main():
    print("\n==============================")
    print("UI LOGIC TEST")
    print("==============================")

    upload = importlib.import_module("app.prospect_upload")
    assert upload.MAX_UPLOAD_BYTES == 5 * 1024 * 1024
    assert callable(upload.load_prospect_csv)
    print("app.prospect_upload imports MAX_UPLOAD_BYTES and load_prospect_csv")

    ui_logic = importlib.import_module("app.ui_logic")
    assert ui_logic.MAX_UPLOAD_BYTES == MAX_UPLOAD_BYTES
    print("app.ui_logic imports the same upload helpers")

    assert normalize_url("zoho.com") == "https://zoho.com"
    assert normalize_url("https://www.zoho.com") == "https://www.zoho.com"
    assert normalize_url("  http://example.com  ") == "http://example.com"
    print("website normalization ok")

    missing = missing_required_fields(
        full_name="",
        phone="",
        email="",
        outreach_email="",
        website="",
        title="",
        industry="",
        has_csv=False,
    )
    assert missing == [
        "Full name",
        "Phone",
        "Email",
        "Outreach email",
        "Industry",
        "Title",
        "Company website",
        "Prospect CSV",
    ]

    none_missing = missing_required_fields(
        full_name="Priya Mehta",
        phone="+919845512210",
        email="priya.mehta@nexusflow.io",
        outreach_email="priya.sales@nexusflow.io",
        website="https://www.zoho.com",
        title="Account Executive",
        industry="Software / SaaS",
        has_csv=True,
    )
    assert none_missing == []
    print("required-field checks ok")

    assert invalid_email_fields("priya@nexusflow.io", "priya.sales@nexusflow.io") is None
    assert invalid_email_fields("not-an-email", "priya@nexusflow.io")
    assert invalid_email_fields("priya@nexusflow.io", "also-not")
    print("email format checks ok")

    assert (
        invalid_catalog_selection("Account Executive", "Software / SaaS")
        is None
    )
    assert invalid_catalog_selection("Plant Head", "Software / SaaS")
    assert invalid_catalog_selection("Account Executive", "Spaceships")
    print("catalog selection checks ok")

    assert upload_too_large(None) is False
    assert upload_too_large(MAX_UPLOAD_BYTES) is False
    assert upload_too_large(MAX_UPLOAD_BYTES + 1) is True
    print("5 MB per-file limit ok")

    rows = preview_prospect_csv(Path("data/uploads/sample_prospects.csv"))
    assert [row["company_name"] for row in rows] == [
        "Asian Paints",
        "Havells India",
    ]
    print("CSV preview ok")

    oversized = Path(tempfile.gettempdir()) / "prospectiq_ui_oversized.csv"
    oversized.write_bytes(b"x" * (MAX_UPLOAD_BYTES + 1))
    try:
        preview_prospect_csv(oversized)
        raise AssertionError("oversized preview should fail")
    except ValueError as exc:
        assert "5 MB" in str(exc)
        print("oversized preview blocked")

    app_dir = str(Path("app").resolve())
    root = str(Path(".").resolve())
    previous = sys.path[:]
    try:
        sys.path = [app_dir] + [p for p in previous if p not in {app_dir, root}]
        if str(root) not in sys.path:
            sys.path.insert(0, root)
        reloaded = importlib.reload(importlib.import_module("app.prospect_upload"))
        assert reloaded.MAX_UPLOAD_BYTES == MAX_UPLOAD_BYTES
        print("imports work when the UI script directory is first on path")
    finally:
        sys.path[:] = previous

    print("\nUI LOGIC TEST PASSED")


if __name__ == "__main__":
    main()
