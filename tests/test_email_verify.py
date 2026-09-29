import os

from app.email_verify import EmailVerifier, otp_required


def main():
    print("\n==============================")
    print("OUTREACH EMAIL VERIFY TEST")
    print("==============================")

    previous = os.environ.get("OTP_REQUIRED")
    os.environ["OTP_REQUIRED"] = "true"

    sent: list[tuple[str, str]] = []
    verifier = EmailVerifier(send_fn=lambda to, code: sent.append((to, code)))

    try:
        verifier.start("not-an-email")
        raise AssertionError("invalid email should fail")
    except ValueError as exc:
        assert "valid outreach email" in str(exc)

    started = verifier.start("Priya.Sales@NexusFlow.io")
    assert started["email"] == "priya.sales@nexusflow.io"
    assert sent[-1][0] == "priya.sales@nexusflow.io"
    code = sent[-1][1]
    assert len(code) == 6
    assert verifier.is_verified("priya.sales@nexusflow.io") is False
    print("code sent")

    try:
        verifier.start("priya.sales@nexusflow.io")
        raise AssertionError("resend cooldown should fail")
    except ValueError as exc:
        assert "wait" in str(exc)
    print("resend cooldown ok")

    try:
        verifier.confirm("priya.sales@nexusflow.io", "000000")
        raise AssertionError("wrong code should fail")
    except ValueError as exc:
        assert "doesn’t match" in str(exc) or "doesn't match" in str(exc)

    verifier.confirm("priya.sales@nexusflow.io", code)
    assert verifier.is_verified("PRIYA.SALES@nexusflow.io") is True
    print("code accepted")

    os.environ["OTP_REQUIRED"] = "false"
    assert otp_required() is False
    assert EmailVerifier(send_fn=lambda *_: None).is_verified("anyone@x.com") is True
    os.environ["OTP_REQUIRED"] = "true"
    assert otp_required() is True
    assert EmailVerifier(send_fn=lambda *_: None).is_verified("anyone@x.com") is False
    if previous is None:
        os.environ.pop("OTP_REQUIRED", None)
    else:
        os.environ["OTP_REQUIRED"] = previous
    print("OTP_REQUIRED flag ok")

    print("\nOUTREACH EMAIL VERIFY TEST PASSED")


if __name__ == "__main__":
    main()
