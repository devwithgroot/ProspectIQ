import os

from fastapi.testclient import TestClient

from app.email_verify import verifier
from app.prospect_upload import MAX_UPLOAD_BYTES
from app.server import app, invalid_email_fields, missing_required_fields, normalize_url


def main():
    print("\n==============================")
    print("API UI CONTRACT TEST")
    print("==============================")

    sent: list[tuple[str, str]] = []
    verifier.reset()
    verifier.send_fn = lambda to, code: sent.append((to, code))

    client = TestClient(app)

    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    print("health ok")

    assert normalize_url("zoho.com") == "https://zoho.com"
    assert normalize_url("https://www.zoho.com") == "https://www.zoho.com"
    assert normalize_url("  http://example.com  ") == "http://example.com"
    print("website normalization ok")

    missing_labels = missing_required_fields(
        full_name="",
        phone="",
        email="",
        outreach_email="",
        website="",
        title="",
        industry="",
        has_csv=False,
    )
    assert missing_labels == [
        "Full name",
        "Phone",
        "Email",
        "Outreach email",
        "Industry",
        "Title",
        "Company website",
        "Prospect CSV",
    ]
    assert (
        missing_required_fields(
            full_name="Priya Mehta",
            phone="+919845512210",
            email="priya.mehta@nexusflow.io",
            outreach_email="priya.sales@nexusflow.io",
            website="https://www.zoho.com",
            title="Account Executive",
            industry="Software / SaaS",
            has_csv=True,
        )
        == []
    )
    print("required-field checks ok")

    assert invalid_email_fields("priya@nexusflow.io", "priya.sales@nexusflow.io") is None
    assert invalid_email_fields("not-an-email", "priya@nexusflow.io")
    assert invalid_email_fields("priya@nexusflow.io", "also-not")
    print("email format checks ok")

    catalog = client.get("/api/catalog")
    assert catalog.status_code == 200
    body = catalog.json()
    assert any(item["label"] == "Software / SaaS" for item in body["industries"])
    assert "Software / SaaS" in body["titles_by_industry"]
    print("catalog ok")

    mock_bundle = client.get("/api/mock/bundle")
    assert mock_bundle.status_code == 200
    bundle = mock_bundle.json()
    assert bundle["user"]["full_name"]
    assert bundle["companies"]
    assert bundle["contacts"]
    print("mock bundle ok")

    previous_otp = os.environ.get("OTP_REQUIRED")
    os.environ["OTP_REQUIRED"] = "false"
    off = client.get("/api/settings")
    assert off.status_code == 200
    assert off.json()["otp_required"] is False
    os.environ["OTP_REQUIRED"] = "true"
    on = client.get("/api/settings")
    assert on.json()["otp_required"] is True
    print("settings otp flag ok")

    preview = client.post(
        "/api/preview",
        files={
            "prospects": (
                "sample.csv",
                b"company_name,website,notes\nAcme,https://acme.com,fit\nAcme,https://acme.com,dup\n",
                "text/csv",
            )
        },
    )
    assert preview.status_code == 200
    staged = preview.json()
    assert staged["count"] == 1
    assert staged["companies"][0]["company_name"] == "Acme"
    print("preview staging ok")

    missing = client.post(
        "/api/research",
        data={
            "full_name": " ",
            "phone": " ",
            "email": " ",
            "outreach_email": " ",
            "website": " ",
            "title": " ",
            "industry": " ",
        },
        files={"prospects": ("prospects.csv", b"company_name\nAcme\n", "text/csv")},
    )
    assert missing.status_code == 400
    assert "Full name" in missing.json()["detail"]
    print("missing fields rejected")

    bad_title = client.post(
        "/api/research",
        data={
            "full_name": "Priya Mehta",
            "phone": "+919845512210",
            "email": "priya@nexusflow.io",
            "outreach_email": "priya.sales@nexusflow.io",
            "website": "zoho.com",
            "title": "Wizard of Sales",
            "industry": "Software / SaaS",
        },
        files={"prospects": ("prospects.csv", b"company_name\nAcme\n", "text/csv")},
    )
    assert bad_title.status_code == 400
    assert "selected from the list" in bad_title.json()["detail"]
    print("freeform title rejected")

    wrong_industry = client.post(
        "/api/research",
        data={
            "full_name": "Priya Mehta",
            "phone": "+919845512210",
            "email": "priya@nexusflow.io",
            "outreach_email": "priya.sales@nexusflow.io",
            "website": "zoho.com",
            "title": "Medical Representative",
            "industry": "Software / SaaS",
        },
        files={"prospects": ("prospects.csv", b"company_name\nAcme\n", "text/csv")},
    )
    assert wrong_industry.status_code == 400
    assert "not a title used in" in wrong_industry.json()["detail"]
    print("cross-industry title rejected")

    not_csv = client.post(
        "/api/research",
        data={
            "full_name": "Priya Mehta",
            "phone": "+919845512210",
            "email": "priya@nexusflow.io",
            "outreach_email": "priya.sales@nexusflow.io",
            "website": "zoho.com",
            "title": "Account Executive",
            "industry": "Software / SaaS",
        },
        files={"prospects": ("prospects.txt", b"nope", "text/plain")},
    )
    assert not_csv.status_code == 400
    assert "CSV" in not_csv.json()["detail"]
    print("non-csv rejected")

    oversized = client.post(
        "/api/research",
        data={
            "full_name": "Priya Mehta",
            "phone": "+919845512210",
            "email": "priya@nexusflow.io",
            "outreach_email": "priya.sales@nexusflow.io",
            "website": "https://www.zoho.com",
            "title": "Account Executive",
            "industry": "Software / SaaS",
        },
        files={
            "prospects": (
                "prospects.csv",
                b"x" * (MAX_UPLOAD_BYTES + 1),
                "text/csv",
            )
        },
    )
    assert oversized.status_code == 400
    assert "5 MB" in oversized.json()["detail"]
    print("5 MB limit rejected")

    started = client.post(
        "/api/verify-email",
        json={"email": "priya.sales@nexusflow.io"},
    )
    assert started.status_code == 200
    assert sent[-1][0] == "priya.sales@nexusflow.io"
    code = sent[-1][1]

    wrong = client.post(
        "/api/verify-email/confirm",
        json={"email": "priya.sales@nexusflow.io", "code": "000000"},
    )
    assert wrong.status_code == 400

    confirmed = client.post(
        "/api/verify-email/confirm",
        json={"email": "priya.sales@nexusflow.io", "code": code},
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["verified"] is True
    print("outreach email verified")

    if previous_otp is None:
        os.environ.pop("OTP_REQUIRED", None)
    else:
        os.environ["OTP_REQUIRED"] = previous_otp

    print("API UI CONTRACT TEST PASSED")


if __name__ == "__main__":
    main()
