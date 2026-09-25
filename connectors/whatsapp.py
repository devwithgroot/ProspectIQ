import os

import requests

from config.excon_schemas import Contact, OutreachDraft, SendResult
from connectors.base import BaseConnector


class WhatsAppConnector(BaseConnector):
    channel = "whatsapp"

    def _deliver(
        self,
        contact: Contact,
        draft: OutreachDraft,
        handle: str,
    ) -> SendResult:
        token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

        if not token or not phone_number_id:
            return SendResult(
                success=False,
                channel=self.channel,
                draft_id=draft.draft_id,
                error="WhatsApp Cloud API credentials are not configured.",
            )

        response = requests.post(
            (
                f"https://graph.facebook.com/v21.0/"
                f"{phone_number_id}/messages"
            ),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "messaging_product": "whatsapp",
                "to": handle.lstrip("+"),
                "type": "text",
                "text": {"body": draft.body},
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        messages = payload.get("messages") or []
        external_id = messages[0].get("id") if messages else None

        return SendResult(
            success=True,
            channel=self.channel,
            draft_id=draft.draft_id,
            external_id=external_id,
        )
