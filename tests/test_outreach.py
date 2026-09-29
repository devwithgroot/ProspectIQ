from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.server import app
from config.excon_schemas import OutreachBatch, OutreachDraft, OutreachPackage
from data.loader import load_mock_bundle


def _payload() -> dict:
    bundle = load_mock_bundle()
    return {
        "user": bundle.user.model_dump(mode="json"),
        "products": [item.model_dump(mode="json") for item in bundle.products],
        "companies": [item.model_dump(mode="json") for item in bundle.companies],
        "company_profiles": [
            item.model_dump(mode="json") for item in bundle.company_profiles
        ],
        "contacts": [item.model_dump(mode="json") for item in bundle.contacts],
        "contact_profiles": [
            item.model_dump(mode="json") for item in bundle.contact_profiles
        ],
    }


def main():
    print("\n==============================")
    print("OUTREACH DRAFT API TEST")
    print("==============================")

    client = TestClient(app)
    missing = client.post("/api/outreach/draft", json={"contact_id": "ct_missing"})
    assert missing.status_code == 400
    print("missing result 400")

    now = datetime.now(timezone.utc)

    class FakeExcon:
        def __init__(self, **kwargs):
            pass

        def prepare(self, **kwargs):
            contact = kwargs["contacts"][0]
            return OutreachBatch(
                batch_id="ob_test",
                user_id=kwargs["user"].user_id,
                company_id=kwargs["company"].company_id,
                created_at=now,
                packages=[
                    OutreachPackage(
                        contact_id=contact.contact_id,
                        profile_id=kwargs["profiles"][0].profile_id,
                        drafts=[
                            OutreachDraft(
                                draft_id="dr_test",
                                contact_id=contact.contact_id,
                                company_id=contact.company_id,
                                profile_id=kwargs["profiles"][0].profile_id,
                                channel="email",
                                subject="Hello",
                                body="Draft body",
                                rationale="Test",
                                created_at=now,
                            )
                        ],
                    )
                ],
            )

    with patch("app.outreach.Excon", FakeExcon):
        ok = client.post(
            "/api/outreach/draft",
            json={"contact_id": "ct_ap_001", "result": _payload()},
        )
        assert ok.status_code == 200
        body = ok.json()
        assert body["contact_name"] == "Amit Sharma"
        assert body["dry_run"] is True
        assert body["drafts"][0]["body"] == "Draft body"
        print("draft from live result ok")

        linkedin = client.post(
            "/api/outreach/draft",
            json={
                "contact_id": "ct_ap_001",
                "channel": "linkedin",
                "result": _payload(),
            },
        )
        assert linkedin.status_code == 200
        print("draft for chosen channel ok")

        unknown = client.post(
            "/api/outreach/draft",
            json={"contact_id": "ct_missing", "result": _payload()},
        )
        assert unknown.status_code == 400
        print("unknown contact 400")

    print("\nOUTREACH DRAFT API TEST PASSED")


if __name__ == "__main__":
    main()
