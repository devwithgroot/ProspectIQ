from __future__ import annotations

from config.excon_schemas import Channel, Contact, DoNotContactEntry


CHANNEL_FALLBACK_ORDER: list[Channel] = [
    "email",
    "linkedin",
    "whatsapp",
    "slack",
    "sms",
]


def normalize(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().lower()


def is_on_dnc(
    contact: Contact,
    dnc: list[DoNotContactEntry],
) -> bool:
    if contact.do_not_contact:
        return True

    email = normalize(contact.email)
    phone = normalize(contact.phone)
    whatsapp = normalize(contact.whatsapp_number)
    contact_id = normalize(contact.contact_id)

    for entry in dnc:
        value = normalize(entry.value)
        if not value:
            continue

        if entry.kind == "contact_id" and value == contact_id:
            return True

        if entry.kind == "email" and email and value == email:
            return True

        if entry.kind == "phone" and value in {phone, whatsapp}:
            return True

    return False


def can_use_channel(
    contact: Contact,
    channel: Channel,
    dnc: list[DoNotContactEntry],
) -> bool:
    if is_on_dnc(contact, dnc):
        return False

    if not contact.consent.allows(channel):
        return False

    return contact.handle_for(channel) is not None


def eligible_channels(
    contact: Contact,
    dnc: list[DoNotContactEntry],
) -> list[Channel]:
    return [
        channel
        for channel in CHANNEL_FALLBACK_ORDER
        if can_use_channel(contact, channel, dnc)
    ]


def select_primary_channel(
    contact: Contact,
    dnc: list[DoNotContactEntry],
) -> Channel | None:
    preferred = contact.preferred_channel
    if can_use_channel(contact, preferred, dnc):
        return preferred

    eligible = eligible_channels(contact, dnc)
    if not eligible:
        return None

    return eligible[0]


def skip_reason(
    contact: Contact,
    dnc: list[DoNotContactEntry],
) -> str | None:
    if is_on_dnc(contact, dnc):
        return "Contact is on the do-not-contact list."

    if select_primary_channel(contact, dnc) is None:
        return "No eligible channel: missing handle or consent."

    return None
