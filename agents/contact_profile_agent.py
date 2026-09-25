from collections.abc import Callable

from config.excon_schemas import (
    Company,
    CompanyProfile,
    Contact,
    ContactProfile,
    Product,
)
from config.schemas import ContactProfileDraft, Evidence
from llm.client import LLMClient
from llm.json_util import generate_model, reason_lines

from app.report_mapper import slug
from config.research_log import get_logger

log = get_logger("contact")


class ContactProfileAgent:
    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm or LLMClient()

    def generate(
        self,
        contact: Contact,
        company: Company,
        company_profile: CompanyProfile,
        products: list[Product],
        evidence: list[Evidence] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> ContactProfile:
        log.info("Contact profile start %s at %s", contact.full_name, company.name)
        if on_progress is not None:
            on_progress(f"Writing a briefing for {contact.full_name}")

        product_summary = "\n".join(
            f"- {product.name}: {product.description}"
            for product in products
        ) or "No matched products."
        signals = "\n".join(
            f"- {signal.description}" for signal in company_profile.signals
        ) or "None provided."
        evidence_summary = "\n".join(
            (
                f"- Title: {item.title}\n"
                f"  URL: {item.url}\n"
                f"  Content: {item.content[:500]}"
            )
            for item in (evidence or [])[:8]
        ) or "No public articles on this person yet."

        prompt = f"""
You are writing a short contact briefing for a salesperson.

Use ONLY the facts below. Do not invent meetings, metrics,
or personal details that are not listed. The company briefing
and any public articles on this person both count.

Seller products:
{product_summary}

Company:
- Name: {company.name}
- Industry: {company.industry}
- Summary: {company_profile.executive_summary}
- Why relevant: {company_profile.why_relevant_to_user}
- Pain points: {", ".join(company_profile.pain_points)}
- Signals:
{signals}
- Suggested company approach: {company_profile.recommended_sales_approach}

Contact:
- Name: {contact.full_name}
- Title: {contact.title}
- Department: {contact.department}
- Seniority: {contact.seniority}
- Decision role: {contact.decision_role}

Public research on this person and company:
{evidence_summary}

Return JSON with:
bio, responsibilities, interests, recent_activity,
communication_style, likely_pain_vs_product, talking_points,
risks, recommended_approach, language.
Keep lists short (2-4 items). Bio is 1-3 sentences.
"""

        try:
            draft = generate_model(
                self.llm,
                ContactProfileDraft,
                prompt,
                max_tokens=700,
            )
            log.info("Contact profile ok %s", contact.full_name)
        except ValueError:
            log.exception("Contact profile fallback for %s", contact.full_name)
            draft = self._fallback(contact, company, company_profile)

        if on_progress is not None:
            for line in reason_lines(draft.likely_pain_vs_product, limit=1):
                on_progress(line)

        return ContactProfile(
            profile_id=slug(contact.contact_id, "pf"),
            contact_id=contact.contact_id,
            company_id=contact.company_id,
            bio=draft.bio,
            responsibilities=draft.responsibilities,
            interests=draft.interests,
            recent_activity=draft.recent_activity,
            communication_style=draft.communication_style,
            likely_pain_vs_product=draft.likely_pain_vs_product,
            talking_points=draft.talking_points,
            risks=draft.risks,
            recommended_approach=draft.recommended_approach,
            language=draft.language or "en",
        )

    def _fallback(
        self,
        contact: Contact,
        company: Company,
        company_profile: CompanyProfile,
    ) -> ContactProfileDraft:
        return ContactProfileDraft(
            bio=(
                f"{contact.full_name} is {contact.title} at {company.name}."
            ),
            responsibilities=[contact.title],
            communication_style="Unknown from public title only.",
            likely_pain_vs_product=company_profile.why_relevant_to_user,
            talking_points=[
                signal.description
                for signal in company_profile.signals[:2]
            ],
            risks=["We only have a public title so far."],
            recommended_approach=(
                "Start from the company briefing and confirm "
                "their role before pitching."
            ),
        )
