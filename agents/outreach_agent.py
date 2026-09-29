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
    Company,
    CompanyProfile,
    User,
)
from connectors.compliance import is_on_dnc, select_primary_channel, skip_reason
from llm.client import LLMClient
from llm.json_util import generate_model


CHANNEL_GUIDANCE = {
    "email": (
        "Write a subject and a 120-180 word email. "
        "Use real line breaks in the body: greeting on its own line, "
        "then two short paragraphs separated by a blank line, "
        "then a sign-off on its own line, then the sender name, "
        "then the sender email. "
        "End with an unsubscribe line such as "
        "'Reply STOP if you would prefer not to receive emails like this.' "
        "Do not write the email as one paragraph."
    ),
    "linkedin": (
        "No subject. Keep the body around 300 characters. "
        "Use real line breaks: greeting on its own line, then a short note. "
        "Conversational, not an email."
    ),
    "whatsapp": (
        "No subject. Short mobile message. "
        "Greeting on its own line, then the note, blank line between thoughts. "
        "No formal sign-off spam."
    ),
    "slack": (
        "No subject. One to three sentences. "
        "Greeting on its own line if you use one. No email tone."
    ),
    "sms": (
        "No subject. Tighter than WhatsApp. "
        "Greeting on its own line. "
        "End with 'Reply STOP to opt out.' on its own line."
    ),
}


class OutreachAgent:
    def __init__(self, llm=None):
        self.llm = llm or LLMClient()

    def prepare_package(
        self,
        user: User,
        products: list[Product],
        company: Company,
        company_profile: CompanyProfile,
        contact: Contact,
        profile: ContactProfile,
        dnc: list[DoNotContactEntry],
        channel: Channel | None = None,
    ) -> OutreachPackage:
        if is_on_dnc(contact, dnc):
            return OutreachPackage(
                contact_id=contact.contact_id,
                profile_id=profile.profile_id,
                drafts=[],
                skipped_reason="Contact is on the do-not-contact list.",
            )

        chosen = channel or select_primary_channel(contact, dnc)
        if chosen is None:
            return OutreachPackage(
                contact_id=contact.contact_id,
                profile_id=profile.profile_id,
                drafts=[],
                skipped_reason=skip_reason(contact, dnc)
                or "No eligible channel: missing handle or consent.",
            )

        content = self._draft_content(
            user=user,
            products=products,
            company=company,
            company_profile=company_profile,
            contact=contact,
            profile=profile,
            channel=chosen,
        )

        now = datetime.now(timezone.utc)
        draft = OutreachDraft(
            draft_id=f"dr_{uuid4().hex[:12]}",
            contact_id=contact.contact_id,
            company_id=company.company_id,
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
        company: Company,
        company_profile: CompanyProfile,
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
                for signal in company_profile.signals
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

Company:
- Name: {company.name}
- Industry: {company.industry}
- Summary: {company_profile.executive_summary}
- Why relevant: {company_profile.why_relevant_to_user}
- Pain points: {", ".join(company_profile.pain_points)}
- Signals:
{signal_summary}
- Recommendation: {company_profile.recommendation} ({company_profile.overall_score})

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
            content.subject = f"{company.name} / {user.company.name}"
        content.body = format_email_body(content.body)

        return content


def format_email_body(body: str) -> str:
    text = " ".join(body.replace("\r\n", "\n").split())
    if not text:
        return ""
    if "\n\n" in body:
        return body.replace("\r\n", "\n").strip()

    parts: list[str] = []
    greeting = ""
    for prefix in ("Hi ", "Hello ", "Hey ", "Dear "):
        if text.lower().startswith(prefix.lower()):
            cut = -1
            for index, char in enumerate(text[:90]):
                if char in ",—–":
                    cut = index
                    break
            if cut > 0:
                greeting = text[:cut].rstrip() + ","
                rest = text[cut + 1 :].strip()
                text = rest[:1].upper() + rest[1:] if rest else ""
            break
    if greeting:
        parts.append(greeting)

    stop = ""
    marker = "reply stop"
    found = text.lower().find(marker)
    if found >= 0:
        stop = text[found:].strip()
        text = text[:found].strip()

    signoff = ""
    for label in (
        "Best regards",
        "Kind regards",
        "Warm regards",
        "Regards",
        "Thank you",
        "Thanks",
        "Sincerely",
        "Best",
    ):
        idx = text.lower().rfind(label.lower())
        if idx >= 0:
            signoff = _format_signoff(text[idx:].strip())
            text = text[:idx].strip()
            break

    parts.extend(_split_paragraphs(text))
    if signoff:
        parts.append(signoff)
    if stop:
        parts.append(stop)
    return "\n\n".join(part for part in parts if part)


def _format_signoff(block: str) -> str:
    lines = [block]
    for label in (
        "Best regards",
        "Kind regards",
        "Warm regards",
        "Regards",
        "Thank you",
        "Thanks",
        "Sincerely",
        "Best",
    ):
        if block.lower().startswith(label.lower()):
            rest = block[len(label) :].lstrip(" ,")
            email = ""
            for token in rest.split():
                if "@" in token:
                    email = token.strip(" .,;")
                    rest = rest.replace(token, "").strip(" .,;")
                    break
            lines = [f"{label},"]
            if rest:
                lines.append(rest)
            if email:
                lines.append(email)
            break
    return "\n".join(lines)


def _split_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    sentences: list[str] = []
    current = ""
    for char in text:
        current += char
        if char in ".!?" and current.strip():
            sentences.append(current.strip())
            current = ""
    if current.strip():
        sentences.append(current.strip())
    chunks: list[str] = []
    buffer: list[str] = []
    for sentence in sentences:
        buffer.append(sentence)
        if len(" ".join(buffer)) >= 160:
            chunks.append(" ".join(buffer))
            buffer = []
    if buffer:
        chunks.append(" ".join(buffer))
    return chunks
