from abc import ABC, abstractmethod

from config.excon_schemas import Contact, OutreachDraft, SendResult
from connectors.compliance import can_use_channel, is_on_dnc


class ConnectorError(PermissionError):
    pass


class BaseConnector(ABC):
    channel: str

    def can_send(
        self,
        contact: Contact,
        dnc: list,
    ) -> bool:
        return can_use_channel(contact, self.channel, dnc)

    def send(
        self,
        contact: Contact,
        draft: OutreachDraft,
        *,
        dry_run: bool,
        dnc: list,
    ) -> SendResult:
        if draft.status != "approved":
            raise ConnectorError(
                f"Draft {draft.draft_id} must be approved before send."
            )

        if draft.channel != self.channel:
            raise ConnectorError(
                f"Draft channel {draft.channel} does not match "
                f"connector {self.channel}."
            )

        if is_on_dnc(contact, dnc):
            raise ConnectorError(
                f"Contact {contact.contact_id} is on the do-not-contact list."
            )

        if not contact.consent.allows(self.channel):
            raise ConnectorError(
                f"Contact {contact.contact_id} has not consented "
                f"to {self.channel}."
            )

        handle = contact.handle_for(self.channel)
        if not handle:
            raise ConnectorError(
                f"Contact {contact.contact_id} has no {self.channel} handle."
            )

        if dry_run:
            print(
                f"[EXCON dry-run] {self.channel} -> {handle}\n"
                f"subject: {draft.subject}\n"
                f"body: {draft.body}"
            )
            return SendResult(
                success=True,
                channel=self.channel,
                draft_id=draft.draft_id,
                external_id=f"dry-run-{draft.draft_id}",
                dry_run=True,
            )

        return self._deliver(contact, draft, handle)

    @abstractmethod
    def _deliver(
        self,
        contact: Contact,
        draft: OutreachDraft,
        handle: str,
    ) -> SendResult:
        pass
