from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from agents.outreach_agent import OutreachAgent
from config.excon_schemas import (
    Contact,
    ContactProfile,
    DoNotContactEntry,
    OutreachBatch,
    OutreachDraft,
    OutreachEvent,
    OutreachPackage,
    Product,
    Prospect,
    SendResult,
    User,
)
from connectors import build_connectors
from connectors.base import ConnectorError


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _env_dry_run() -> bool:
    value = os.getenv("EXCON_DRY_RUN", "true").strip().lower()
    return value in {"1", "true", "yes", "on"}


class Excon:
    def __init__(
        self,
        *,
        llm=None,
        dry_run: bool | None = None,
        dnc: list[DoNotContactEntry] | None = None,
    ):
        self.outreach = OutreachAgent(llm=llm)
        self.dry_run = _env_dry_run() if dry_run is None else dry_run
        self.dnc = list(dnc or [])
        self.connectors = build_connectors()
        self.drafts: dict[str, OutreachDraft] = {}
        self.contacts: dict[str, Contact] = {}
        self.events: list[OutreachEvent] = []

    def prepare(
        self,
        user: User,
        prospect: Prospect,
        profiles: list[ContactProfile],
        contacts: list[Contact],
        products: list[Product],
        dnc: list[DoNotContactEntry] | None = None,
    ) -> OutreachBatch:
        if dnc is not None:
            self.dnc = list(dnc)

        contact_map = {contact.contact_id: contact for contact in contacts}
        self.contacts.update(contact_map)

        packages = []

        for profile in profiles:
            contact = contact_map.get(profile.contact_id)
            if contact is None:
                packages.append(
                    OutreachPackage(
                        contact_id=profile.contact_id,
                        profile_id=profile.profile_id,
                        drafts=[],
                        skipped_reason="Contact record was not provided.",
                    )
                )
                continue

            if contact.prospect_id != prospect.prospect_id:
                packages.append(
                    OutreachPackage(
                        contact_id=contact.contact_id,
                        profile_id=profile.profile_id,
                        drafts=[],
                        skipped_reason="Contact does not belong to this prospect.",
                    )
                )
                continue

            package = self.outreach.prepare_package(
                user=user,
                products=products,
                prospect=prospect,
                contact=contact,
                profile=profile,
                dnc=self.dnc,
            )
            packages.append(package)

            for draft in package.drafts:
                self.drafts[draft.draft_id] = draft
                self._record(
                    event_type="drafted",
                    draft=draft,
                    actor="system",
                    detail=draft.rationale,
                )

        return OutreachBatch(
            batch_id=f"ob_{uuid4().hex[:12]}",
            user_id=user.user_id,
            prospect_id=prospect.prospect_id,
            packages=packages,
            created_at=_utc_now(),
        )

    def edit(
        self,
        draft_id: str,
        subject: str | None = None,
        body: str | None = None,
    ) -> OutreachDraft:
        draft = self._get_draft(draft_id)

        if subject is not None:
            draft.subject = subject
        if body is not None:
            draft.body = body

        draft.status = "draft"
        draft.updated_at = _utc_now()
        self.drafts[draft_id] = draft
        self._record(
            event_type="edited",
            draft=draft,
            actor="user",
            detail="Draft edited; approval reset.",
        )
        return draft

    def approve(self, draft_id: str) -> OutreachDraft:
        draft = self._get_draft(draft_id)
        if draft.status == "sent":
            raise ValueError(f"Draft {draft_id} has already been sent.")

        draft.status = "approved"
        draft.updated_at = _utc_now()
        self.drafts[draft_id] = draft
        self._record(event_type="approved", draft=draft, actor="user")
        return draft

    def reject(self, draft_id: str) -> OutreachDraft:
        draft = self._get_draft(draft_id)
        if draft.status == "sent":
            raise ValueError(f"Draft {draft_id} has already been sent.")

        draft.status = "rejected"
        draft.updated_at = _utc_now()
        self.drafts[draft_id] = draft
        self._record(event_type="rejected", draft=draft, actor="user")
        return draft

    def send(self, draft_id: str) -> SendResult:
        draft = self._get_draft(draft_id)
        contact = self.contacts.get(draft.contact_id)
        if contact is None:
            raise ValueError(
                f"No contact stored for draft {draft_id}."
            )

        connector = self.connectors.get(draft.channel)
        if connector is None:
            raise ValueError(f"No connector for channel {draft.channel}.")

        try:
            result = connector.send(
                contact,
                draft,
                dry_run=self.dry_run,
                dnc=self.dnc,
            )
        except ConnectorError as exc:
            self._record(
                event_type="send_failed",
                draft=draft,
                actor="user",
                detail=str(exc),
            )
            raise

        if result.success:
            draft.status = "sent"
            draft.updated_at = _utc_now()
            self.drafts[draft_id] = draft
            self._record(
                event_type="sent",
                draft=draft,
                actor="user",
                detail=result.external_id,
            )
        else:
            self._record(
                event_type="send_failed",
                draft=draft,
                actor="user",
                detail=result.error,
            )

        return result

    def _get_draft(self, draft_id: str) -> OutreachDraft:
        draft = self.drafts.get(draft_id)
        if draft is None:
            raise KeyError(f"Unknown draft_id: {draft_id}")
        return draft

    def _record(
        self,
        event_type: str,
        draft: OutreachDraft,
        actor: str,
        detail: str | None = None,
    ) -> None:
        self.events.append(
            OutreachEvent(
                event_id=f"ev_{uuid4().hex[:12]}",
                event_type=event_type,
                timestamp=_utc_now(),
                draft_id=draft.draft_id,
                contact_id=draft.contact_id,
                channel=draft.channel,
                actor=actor,
                detail=detail,
            )
        )
