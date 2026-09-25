from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


Channel = Literal["email", "linkedin", "whatsapp", "slack", "sms"]

DecisionRole = Literal[
    "economic_buyer",
    "champion",
    "influencer",
    "blocker",
]

DraftStatus = Literal["draft", "approved", "rejected", "sent"]

EventType = Literal[
    "drafted",
    "edited",
    "approved",
    "rejected",
    "sent",
    "send_failed",
]

DncKind = Literal["email", "phone", "contact_id"]


class SellerCompany(BaseModel):
    name: str
    industry: str
    website: str
    size: str
    description: str
    headquarters: str | None = None


class SenderVoice(BaseModel):
    tone: str
    signature: str
    calendar_link: str | None = None
    cta: str


class User(BaseModel):
    user_id: str
    full_name: str
    title: str
    email: str
    phone: str | None = None
    linkedin_url: str | None = None
    locale: str = "en-IN"
    product_ids: list[str] = Field(default_factory=list)
    company: SellerCompany
    voice: SenderVoice


class Product(BaseModel):
    product_id: str
    name: str
    category: str
    description: str
    icp: str
    target_industries: list[str]
    value_props: list[str]
    use_cases: list[str]
    differentiators: list[str]
    objections: list[str]
    typical_buyers: list[str]
    pricing_model: str | None = None
    proof_points: list[str] = Field(default_factory=list)


class ProspectSignal(BaseModel):
    type: str
    description: str
    strength: str
    evidence: str | None = None


class Prospect(BaseModel):
    prospect_id: str
    company_name: str
    website: str | None = None
    industry: str
    headquarters: str | None = None
    employee_count: int | None = None
    founded_year: int | None = None
    description: str
    products_services: list[str] = Field(default_factory=list)
    signals: list[ProspectSignal] = Field(default_factory=list)
    pain_points: list[str] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=100.0)
    recommendation: str
    why_relevant_to_user: str
    matched_product_ids: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)


class ChannelConsent(BaseModel):
    email: bool = False
    linkedin: bool = False
    whatsapp: bool = False
    slack: bool = False
    sms: bool = False

    def allows(self, channel: Channel) -> bool:
        return bool(getattr(self, channel, False))


class Contact(BaseModel):
    contact_id: str
    prospect_id: str
    full_name: str
    title: str
    seniority: str
    department: str
    decision_role: DecisionRole
    email: str | None = None
    phone: str | None = None
    linkedin_url: str | None = None
    whatsapp_number: str | None = None
    slack_user_id: str | None = None
    preferred_channel: Channel
    consent: ChannelConsent
    do_not_contact: bool = False
    timezone: str = "Asia/Kolkata"

    def handle_for(self, channel: Channel) -> str | None:
        mapping: dict[Channel, str | None] = {
            "email": self.email,
            "linkedin": self.linkedin_url,
            "whatsapp": self.whatsapp_number,
            "slack": self.slack_user_id,
            "sms": self.phone,
        }
        value = mapping[channel]
        if value is None:
            return None
        value = value.strip()
        return value or None


class ContactProfile(BaseModel):
    profile_id: str
    contact_id: str
    prospect_id: str
    bio: str
    responsibilities: list[str] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    recent_activity: list[str] = Field(default_factory=list)
    communication_style: str
    likely_pain_vs_product: str
    talking_points: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    recommended_approach: str
    language: str = "en"


class DoNotContactEntry(BaseModel):
    kind: DncKind
    value: str
    reason: str | None = None


class DraftContent(BaseModel):
    channel: Channel
    subject: str | None = None
    body: str
    rationale: str


class OutreachDraft(BaseModel):
    draft_id: str
    contact_id: str
    prospect_id: str
    profile_id: str
    channel: Channel
    subject: str | None = None
    body: str
    rationale: str
    is_primary: bool = True
    status: DraftStatus = "draft"
    created_at: datetime
    updated_at: datetime | None = None


class OutreachPackage(BaseModel):
    contact_id: str
    profile_id: str
    drafts: list[OutreachDraft] = Field(default_factory=list)
    skipped_reason: str | None = None


class OutreachBatch(BaseModel):
    batch_id: str
    user_id: str
    prospect_id: str
    packages: list[OutreachPackage] = Field(default_factory=list)
    created_at: datetime


class OutreachEvent(BaseModel):
    event_id: str
    event_type: EventType
    timestamp: datetime
    draft_id: str | None = None
    contact_id: str | None = None
    channel: Channel | None = None
    actor: str = "system"
    detail: str | None = None


class SendResult(BaseModel):
    success: bool
    channel: Channel
    draft_id: str
    external_id: str | None = None
    error: str | None = None
    dry_run: bool = False
