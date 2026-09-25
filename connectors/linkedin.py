from config.excon_schemas import Contact, OutreachDraft, SendResult
from connectors.base import BaseConnector


class LinkedInConnector(BaseConnector):
    channel = "linkedin"

    def _deliver(
        self,
        contact: Contact,
        draft: OutreachDraft,
        handle: str,
    ) -> SendResult:
        return SendResult(
            success=False,
            channel=self.channel,
            draft_id=draft.draft_id,
            error=(
                "LinkedIn live send is not enabled. "
                "Use dry-run or an official partner API later. "
                f"Target profile: {handle}"
            ),
        )
