import os
import smtplib
from email.message import EmailMessage

from config.excon_schemas import Contact, OutreachDraft, SendResult
from connectors.base import BaseConnector


class EmailConnector(BaseConnector):
    channel = "email"

    def _deliver(
        self,
        contact: Contact,
        draft: OutreachDraft,
        handle: str,
    ) -> SendResult:
        host = os.getenv("SMTP_HOST")
        sender = os.getenv("SMTP_FROM")

        if not host or not sender:
            return SendResult(
                success=False,
                channel=self.channel,
                draft_id=draft.draft_id,
                error="SMTP_HOST or SMTP_FROM is not configured.",
            )

        message = EmailMessage()
        message["From"] = sender
        message["To"] = handle
        message["Subject"] = draft.subject or "(no subject)"
        message.set_content(draft.body)

        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")

        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(message)

        return SendResult(
            success=True,
            channel=self.channel,
            draft_id=draft.draft_id,
            external_id=handle,
        )
