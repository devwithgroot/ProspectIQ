import os

import requests

from config.excon_schemas import Contact, OutreachDraft, SendResult
from connectors.base import BaseConnector


class SmsConnector(BaseConnector):
    channel = "sms"

    def _deliver(
        self,
        contact: Contact,
        draft: OutreachDraft,
        handle: str,
    ) -> SendResult:
        account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        from_number = os.getenv("TWILIO_FROM_NUMBER")

        if not account_sid or not auth_token or not from_number:
            return SendResult(
                success=False,
                channel=self.channel,
                draft_id=draft.draft_id,
                error="Twilio SMS credentials are not configured.",
            )

        response = requests.post(
            (
                f"https://api.twilio.com/2010-04-01/Accounts/"
                f"{account_sid}/Messages.json"
            ),
            auth=(account_sid, auth_token),
            data={
                "From": from_number,
                "To": handle,
                "Body": draft.body,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        return SendResult(
            success=True,
            channel=self.channel,
            draft_id=draft.draft_id,
            external_id=payload.get("sid"),
        )
