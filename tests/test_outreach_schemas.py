from datetime import datetime, timezone

from config.excon_schemas import (
    ChannelConsent,
    DraftContent,
    OutreachDraft,
    SendResult,
)
from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("EXCON SCHEMA TEST")
    print("==============================")

    bundle = load_mock_bundle()
    contact = bundle.contact_map()["ct_ap_001"]

    assert contact.handle_for("email") == "amit.sharma@asianpaints.com"
    assert contact.consent.allows("email") is True
    assert contact.handle_for("slack") is None

    rohan = bundle.contact_map()["ct_ap_003"]
    assert rohan.handle_for("email") is None
    assert rohan.handle_for("whatsapp") == "+919820011003"

    consent = ChannelConsent(email=True, sms=False)
    assert consent.allows("email") is True
    assert consent.allows("sms") is False

    now = datetime.now(timezone.utc)
    draft = OutreachDraft(
        draft_id="dr_test",
        contact_id=contact.contact_id,
        prospect_id=contact.prospect_id,
        profile_id="pf_ap_001",
        channel="email",
        subject="Hello",
        body="Body",
        rationale="Test",
        created_at=now,
    )
    assert draft.status == "draft"

    content = DraftContent.model_validate(
        {
            "channel": "linkedin",
            "subject": None,
            "body": "Short note",
            "rationale": "Primary channel",
        }
    )
    assert content.channel == "linkedin"

    result = SendResult(
        success=True,
        channel="email",
        draft_id="dr_test",
        dry_run=True,
    )
    assert result.dry_run is True

    print("EXCON SCHEMA TEST PASSED")


if __name__ == "__main__":
    main()
