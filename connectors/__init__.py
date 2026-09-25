from __future__ import annotations

from connectors.base import BaseConnector
from connectors.email import EmailConnector
from connectors.linkedin import LinkedInConnector
from connectors.slack import SlackConnector
from connectors.sms import SmsConnector
from connectors.whatsapp import WhatsAppConnector


def build_connectors() -> dict[str, BaseConnector]:
    return {
        "email": EmailConnector(),
        "linkedin": LinkedInConnector(),
        "whatsapp": WhatsAppConnector(),
        "slack": SlackConnector(),
        "sms": SmsConnector(),
    }


__all__ = [
    "BaseConnector",
    "EmailConnector",
    "LinkedInConnector",
    "SlackConnector",
    "SmsConnector",
    "WhatsAppConnector",
    "build_connectors",
]
