from __future__ import annotations

import os
import secrets
import smtplib
import time
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Callable

from dotenv import load_dotenv

load_dotenv()


CODE_TTL_SECONDS = 10 * 60
RESEND_SECONDS = 30
MAX_ATTEMPTS = 5
_OTP_TRUE = {"1", "true", "yes", "on"}


def otp_required() -> bool:
    return os.getenv("OTP_REQUIRED", "false").strip().lower() in _OTP_TRUE


def normalize_email(value: str) -> str:
    return value.strip().lower()


def is_email(value: str) -> bool:
    text = normalize_email(value)
    return "@" in text and "." in text.split("@")[-1] and " " not in text


def send_verification_email(to: str, code: str) -> None:
    host = os.getenv("SMTP_HOST")
    sender = os.getenv("SMTP_FROM")
    if not host or not sender:
        raise RuntimeError(
            "We couldn’t send a code because email sending isn’t set up yet."
        )

    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = "Your ProspectIQ verification code"
    message.set_content(
        f"Your ProspectIQ verification code is {code}.\n\n"
        "It expires in 10 minutes. If you didn’t ask for this, ignore the email."
    )

    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        if user and password:
            server.login(user, password)
        server.send_message(message)


@dataclass
class _Pending:
    code: str
    expires_at: float
    sent_at: float
    attempts: int = 0


class EmailVerifier:
    def __init__(self, send_fn: Callable[[str, str], None] | None = None):
        self.send_fn = send_fn or send_verification_email
        self._pending: dict[str, _Pending] = {}
        self._verified: set[str] = set()

    def reset(self) -> None:
        self._pending.clear()
        self._verified.clear()

    def start(self, email: str) -> dict[str, int | str]:
        address = normalize_email(email)
        if not is_email(address):
            raise ValueError("Please enter a valid outreach email.")

        now = time.time()
        existing = self._pending.get(address)
        if existing and now - existing.sent_at < RESEND_SECONDS:
            wait = int(RESEND_SECONDS - (now - existing.sent_at))
            raise ValueError(
                f"Please wait {wait} seconds before requesting another code."
            )

        code = f"{secrets.randbelow(1_000_000):06d}"
        self.send_fn(address, code)
        self._pending[address] = _Pending(
            code=code,
            expires_at=now + CODE_TTL_SECONDS,
            sent_at=now,
        )
        self._verified.discard(address)
        return {"email": address, "expires_in": CODE_TTL_SECONDS}

    def confirm(self, email: str, code: str) -> None:
        address = normalize_email(email)
        pending = self._pending.get(address)
        if pending is None:
            raise ValueError("Send a code to that email first.")
        if time.time() > pending.expires_at:
            self._pending.pop(address, None)
            raise ValueError("That code has expired. Request a new one.")
        pending.attempts += 1
        if pending.attempts > MAX_ATTEMPTS:
            self._pending.pop(address, None)
            raise ValueError("Too many tries. Request a new code.")
        if code.strip() != pending.code:
            raise ValueError("That code doesn’t match. Try again.")
        self._pending.pop(address, None)
        self._verified.add(address)

    def is_verified(self, email: str) -> bool:
        if not otp_required():
            return True
        return normalize_email(email) in self._verified


verifier = EmailVerifier()
