from __future__ import annotations

from config.excon_schemas import ChannelConsent, Contact
from config.schemas import PersonData

from app.report_mapper import slug


_BUYER_MARKERS = (
    "ceo",
    "founder",
    "owner",
    "president",
    "managing director",
    "cfo",
    "coo",
    "chief",
    "vice president",
    "vp ",
    " vp",
)
_CHAMPION_MARKERS = (
    "head",
    "director",
    "transformation",
    "digital",
    "innovation",
)


def person_display_name(person: PersonData) -> str:
    parts = [person.first_name or "", person.last_name or ""]
    joined = " ".join(part for part in parts if part.strip()).strip()
    return joined or (person.name or "").strip()


def _decision_role(title: str) -> str:
    text = title.lower()
    if any(marker in text for marker in _BUYER_MARKERS):
        return "economic_buyer"
    if any(marker in text for marker in _CHAMPION_MARKERS):
        return "champion"
    return "influencer"


def person_to_contact(person: PersonData, company_id: str) -> Contact | None:
    full_name = person_display_name(person)
    if not full_name:
        return None

    title = (person.title or "Unknown role").strip()
    email = (person.email or "").strip() or None
    phone = (person.mobile or "").strip() or None
    linkedin = (person.linkedin_url or "").strip() or None
    department = (
        person.departments[0].strip()
        if person.departments and person.departments[0].strip()
        else "Unknown"
    )
    if linkedin:
        preferred = "linkedin"
    elif email:
        preferred = "email"
    elif phone:
        preferred = "sms"
    else:
        preferred = "linkedin"

    return Contact(
        contact_id=slug(person.id or full_name, "ct"),
        company_id=company_id,
        full_name=full_name,
        title=title,
        seniority=(person.seniority or "unknown").strip() or "unknown",
        department=department,
        decision_role=_decision_role(title),
        email=email,
        phone=phone,
        linkedin_url=linkedin,
        preferred_channel=preferred,
        consent=ChannelConsent(
            email=False,
            linkedin=bool(linkedin),
            whatsapp=False,
            slack=False,
            sms=False,
        ),
    )
