from datetime import datetime, timezone

from config.excon_schemas import OutreachDraft
from connectors.base import ConnectorError
from connectors.email import EmailConnector
from connectors.linkedin import LinkedInConnector
from connectors.slack import SlackConnector
from data.loader import load_mock_bundle


def _draft(contact_id: str, channel: str, status: str = "approved") -> OutreachDraft:
    now = datetime.now(timezone.utc)
    return OutreachDraft(
        draft_id="dr_connector",
        contact_id=contact_id,
        company_id="pr_asian_paints",
        profile_id="pf_ap_001",
        channel=channel,
        subject="Subject" if channel == "email" else None,
        body="Body",
        rationale="Test",
        status=status,
        created_at=now,
    )


def main():
    print("\n==============================")
    print("CONNECTOR GATE TEST")
    print("==============================")

    bundle = load_mock_bundle()
    amit = bundle.contact_map()["ct_ap_001"]
    deepak = bundle.contact_map()["ct_ap_004"]
    vikram = bundle.contact_map()["ct_hv_002"]
    arjun = bundle.contact_map()["ct_ts_002"]

    email = EmailConnector()

    try:
        email.send(
            amit,
            _draft(amit.contact_id, "email", status="draft"),
            dry_run=True,
            dnc=bundle.dnc,
        )
        raise AssertionError("Draft status should block send")
    except ConnectorError as exc:
        print(f"unapproved blocked: {exc}")

    try:
        email.send(
            deepak,
            _draft(deepak.contact_id, "email"),
            dry_run=True,
            dnc=bundle.dnc,
        )
        raise AssertionError("DNC should block send")
    except ConnectorError as exc:
        print(f"dnc blocked: {exc}")

    try:
        email.send(
            vikram,
            _draft(vikram.contact_id, "sms"),
            dry_run=True,
            dnc=bundle.dnc,
        )
        raise AssertionError("Channel mismatch should block send")
    except ConnectorError as exc:
        print(f"channel mismatch blocked: {exc}")

    result = email.send(
        amit,
        _draft(amit.contact_id, "email"),
        dry_run=True,
        dnc=bundle.dnc,
    )
    assert result.success is True
    assert result.dry_run is True
    print(f"email dry-run: {result.external_id}")

    slack = SlackConnector()
    slack_result = slack.send(
        arjun,
        _draft(arjun.contact_id, "slack"),
        dry_run=True,
        dnc=bundle.dnc,
    )
    assert slack_result.success is True
    print(f"slack dry-run: {slack_result.external_id}")

    linkedin = LinkedInConnector()
    live = linkedin.send(
        amit,
        _draft(amit.contact_id, "linkedin"),
        dry_run=False,
        dnc=bundle.dnc,
    )
    assert live.success is False
    assert "not enabled" in (live.error or "")
    print(f"linkedin live stub: {live.error}")

    print("\nCONNECTOR GATE TEST PASSED")


if __name__ == "__main__":
    main()
