import os

import requests

from config.excon_schemas import Contact, OutreachDraft, SendResult
from connectors.base import BaseConnector


class SlackConnector(BaseConnector):
    channel = "slack"

    def _deliver(
        self,
        contact: Contact,
        draft: OutreachDraft,
        handle: str,
    ) -> SendResult:
        token = os.getenv("SLACK_BOT_TOKEN")
        if not token:
            return SendResult(
                success=False,
                channel=self.channel,
                draft_id=draft.draft_id,
                error="SLACK_BOT_TOKEN is not configured.",
            )

        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "channel": handle,
                "text": draft.body,
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()

        if not payload.get("ok"):
            return SendResult(
                success=False,
                channel=self.channel,
                draft_id=draft.draft_id,
                error=payload.get("error", "Slack API error"),
            )

        return SendResult(
            success=True,
            channel=self.channel,
            draft_id=draft.draft_id,
            external_id=payload.get("ts"),
        )
