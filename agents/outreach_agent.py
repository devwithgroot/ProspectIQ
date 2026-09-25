from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from config.excon_schemas import (
    Channel,
    Contact,
    ContactProfile,
    DoNotContactEntry,
    DraftContent,
    OutreachDraft,
    OutreachPackage,
    Product,
    Prospect,
    User,
)
from connectors.compliance import select_primary_channel, skip_reason
from llm.client import LLMClient
from llm.json_util import generate_model


CHANNEL_GUIDANCE = {
    "email": (
        "Write a subject and a 120-180 word email body. "
        "End with an unsubscribe line such as "
        "'Reply STOP if you would prefer not to receive emails like this.'"
    ),
    "linkedin": (
        "No subject. Keep the body around 300 characters. "
        "Conversational, not an email."
    ),
    "whatsapp": (
        "No subject. Short mobile message. No formal sign-off spam."
    ),
    "slack": (
        "No subject. One to three sentences. No email tone."
    ),
    "sms": (
        "No subject. Tighter than WhatsApp. "
        "End with 'Reply STOP to opt out.'"
    ),
}


class OutreachAgent:
    def __init__(self, llm=None):
        self.llm = llm or LLMClient()

    def prepare_package(
        self,
        user: User,
        products: list[Product],
        prospect: Prospect,
        contact: Contact,
        profile: ContactProfile,
        dnc: list[DoNotContactEntry],
    ) -> OutreachPackage:
        reason = skip_reason(contact, dnc)
        if reason:
            return OutreachPackage(
                contact_id=contact.contact_id,
                profile_id=profile.profile_id,
                drafts=[],
                skipped_reason=reason,
            )

        channel = select_primary_channel(contact, dnc)
        if channel is None:
            return OutreachPackage(
                contact_id=contact.contact_id,
                profile_id=profile.profile_id,
                drafts=[],
                skipped_reason="No eligible channel: missing handle or consent.",
            )

        content = self._draft_content(
            user=user,
            products=products,
            prospect=prospect,
            contact=contact,
            profile=profile,
            channel=channel,
        )

        now = datetime.now(timezone.utc)
        draft = OutreachDraft(
            draft_id=f"dr_{uuid4().hex[:12]}",
            contact_id=contact.contact_id,
            prospect_id=prospect.prospect_id,
            profile_id=profile.profile_id,
            channel=content.channel,
            subject=content.subject,
            body=content.body,
            rationale=content.rationale,
            is_primary=True,
            status="draft",
            created_at=now,
            updated_at=now,
        )

        return OutreachPackage(
            contact_id=contact.contact_id,
            profile_id=profile.profile_id,
            drafts=[draft],
        )

    def _draft_content(
        self,
        user: User,
        products: list[Product],
        prospect: Prospect,
        contact: Contact,
        profile: ContactProfile,
        channel: Channel,
    ) -> DraftContent:
        product_summary = "\n".join(
            [
                (
                    f"- {product.name}: {product.description}\n"
                    f"  Value props: {', '.join(product.value_props)}\n"
                    f"  Typical buyers: {', '.join(product.typical_buyers)}"
                )
                for product in products
            ]
        ) or "No matched products."

        signal_summary = "\n".join(
            [
                f"- {signal.type} ({signal.strength}): {signal.description}"
                for signal in prospect.signals
            ]
        ) or "None provided."

        prompt = f"""
You are the ProspectIQ outreach writer.

Write ONE outreach draft for the target channel.
Use ONLY the facts below. Do not invent titles, metrics,
meetings, products, or personal details.

Seller:
- Name: {user.full_name}
- Title: {user.title}
- Company: {user.company.name} — {user.company.description}
- Tone: {user.voice.tone}
- CTA: {user.voice.cta}
- Signature: {user.voice.signature}
- Calendar: {user.voice.calendar_link or "none"}

Matched products:
{product_summary}

Prospect company:
- Name: {prospect.company_name}
- Industry: {prospect.industry}
- Summary: {prospect.description}
- Why relevant: {prospect.why_relevant_to_user}
- Pain points: {", ".join(prospect.pain_points)}
- Signals:
{signal_summary}
- Recommendation: {prospect.recommendation} ({prospect.overall_score})

Contact:
- Name: {contact.full_name}
- Title: {contact.title}
- Department: {contact.department}
- Seniority: {contact.seniority}
- Decision role: {contact.decision_role}

Contact profile:
- Bio: {profile.bio}
- Responsibilities: {", ".join(profile.responsibilities)}
- Interests: {", ".join(profile.interests)}
- Recent activity: {" | ".join(profile.recent_activity)}
- Communication style: {profile.communication_style}
- Likely pain vs product: {profile.likely_pain_vs_product}
- Talking points: {", ".join(profile.talking_points)}
- Risks: {", ".join(profile.risks)}
- Recommended approach: {profile.recommended_approach}

Target channel: {channel}
Channel rules: {CHANNEL_GUIDANCE[channel]}

Return ONLY valid JSON:
{{
  "channel": "{channel}",
  "subject": "email subject or null",
  "body": "message body",
  "rationale": "brief explanation of why this angle"
}}
"""

        content = generate_model(
            self.llm,
            DraftContent,
            prompt,
            temperature=0.0,
            max_tokens=700,
        )

        if content.channel != channel:
            content.channel = channel

        if channel != "email":
            content.subject = None
        elif not content.subject:
            content.subject = (
                f"{prospect.company_name} / {user.company.name}"
            )

        return content
