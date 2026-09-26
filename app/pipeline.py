from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from agents.contact_profile_agent import ContactProfileAgent
from app.onboarding import OnboardingAgent
from app.orchestrator import ProspectIQ
from app.people_mapper import person_to_contact
from app.prospect_upload import UploadedProspect, company_domain_from_website, load_prospect_csv
from app.report_mapper import report_to_company
from tools.people_data import PeopleDataTool
from config.excon_schemas import (
    Company,
    CompanyProfile,
    Contact,
    ContactProfile,
    Product,
    User,
)


RUNS_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"
PEOPLE_PER_COMPANY = 3


class PipelineResult(BaseModel):
    user: User
    products: list[Product]
    uploaded: list[UploadedProspect]
    companies: list[Company]
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    contacts: list[Contact] = Field(default_factory=list)
    contact_profiles: list[ContactProfile] = Field(default_factory=list)


class ResearchCancelled(Exception):
    def __init__(self, result: PipelineResult | None = None) -> None:
        super().__init__("Research stopped.")
        self.result = result


class ResearchSkipped(Exception):
    pass


class SellerPipeline:
    def __init__(self):
        self.analyzer = ProspectIQ()
        self.onboarder = OnboardingAgent()
        self.contact_profiler = ContactProfileAgent()

    def run(
        self,
        *,
        full_name: str,
        phone: str,
        email: str,
        outreach_email: str | None = None,
        website: str,
        prospects_csv: str | Path,
        title: str,
        industry: str,
        outreach_email_verified: bool = True,
        on_progress: Callable[[str], None] | None = None,
    ) -> PipelineResult:
        def note(message: str) -> None:
            print(message)
            if on_progress is not None:
                on_progress(message)

        user: User | None = None
        products: list[Product] = []
        uploaded: list[UploadedProspect] = []
        companies: list[Company] = []
        company_profiles: list[CompanyProfile] = []
        contacts: list[Contact] = []
        contact_profiles: list[ContactProfile] = []

        try:
            print("\n==============================")
            print("SELLER ONBOARDING")
            print("==============================")

            user, products = self.onboarder.enroll(
                full_name=full_name,
                phone=phone,
                email=email,
                outreach_email=outreach_email or email,
                outreach_email_verified=outreach_email_verified,
                website=website,
                title=title,
                industry=industry,
                on_progress=note,
            )

            print(f"Seller: {user.full_name} <{user.email}>")
            print(f"Outreach from: {user.outreach_email}")
            print(f"Company: {user.company.name}")
            print(f"Products: {', '.join(product.name for product in products)}")
            note(
                f"Got it — {user.company.name}"
                + (
                    f", selling {', '.join(product.name for product in products[:3])}"
                    if products
                    else ""
                )
            )

            uploaded = load_prospect_csv(prospects_csv)
            print(f"\nUploaded prospects: {len(uploaded)}")

            product_names = ", ".join(product.name for product in products)

            for index, row in enumerate(uploaded, start=1):
                print("\n==============================")
                print(f"ORCHESTRATOR {index}/{len(uploaded)}: {row.company_name}")
                print("==============================")

                research_goal = (
                    f"Determine whether {row.company_name} is a high-value "
                    f"B2B sales prospect for {user.company.name}, which sells "
                    f"{product_names}. Also find who to talk to there "
                    f"(buyers, champions, and relevant leaders) so we can "
                    f"build contact profiles."
                )

                try:
                    if len(uploaded) == 1:
                        note(f"Looking into {row.company_name}")
                    else:
                        note(
                            f"Looking into {row.company_name} "
                            f"({index}/{len(uploaded)})"
                        )
                    report = self.analyzer.analyze(
                        company_name=row.company_name,
                        research_goal=research_goal,
                        company_domain=company_domain_from_website(row.website),
                        on_progress=note,
                    )
                    company, profile = report_to_company(
                        report=report,
                        uploaded=row,
                        user=user,
                        products=products,
                    )
                    companies.append(company)
                    company_profiles.append(profile)
                    note(f"Ready with the {row.company_name} briefing")
                    found = self._find_people(
                        company,
                        profile,
                        products,
                        note,
                        company_evidence=list(
                            getattr(self.analyzer.last_state, "evidence", []) or []
                        ),
                    )
                    contacts.extend(found[0])
                    contact_profiles.extend(found[1])
                    if index < len(uploaded):
                        note("Moving to the next company")
                except ResearchSkipped:
                    note(f"Skipped {row.company_name}")
                    continue

            note("Putting your briefings together")
            result = PipelineResult(
                user=user,
                products=products,
                uploaded=uploaded,
                companies=companies,
                company_profiles=company_profiles,
                contacts=contacts,
                contact_profiles=contact_profiles,
            )
            saved = save_run(result)
            print(f"\nSaved run to {saved}")
            return result
        except ResearchCancelled:
            if user is None or not companies:
                raise ResearchCancelled() from None
            result = PipelineResult(
                user=user,
                products=products,
                uploaded=uploaded,
                companies=companies,
                company_profiles=company_profiles,
                contacts=contacts,
                contact_profiles=contact_profiles,
            )
            saved = save_run(result)
            print(f"\nSaved partial run to {saved}")
            raise ResearchCancelled(result) from None

    def _find_people(
        self,
        company: Company,
        company_profile: CompanyProfile,
        products: list[Product],
        note: Callable[[str], None],
        company_evidence: list | None = None,
    ) -> tuple[list[Contact], list[ContactProfile]]:
        note(f"Finding people at {company.name}")
        try:
            people = PeopleDataTool().execute(company=company.name, limit=5)
        except Exception as exc:
            print(f"[People] search failed ({exc})")
            note(f"Couldn’t find people at {company.name} yet")
            return [], []

        seen: set[str] = set()
        contacts: list[Contact] = []
        for person in people:
            contact = person_to_contact(person, company.company_id)
            if contact is None or contact.contact_id in seen:
                continue
            seen.add(contact.contact_id)
            contacts.append(contact)
            if len(contacts) >= PEOPLE_PER_COMPANY:
                break

        if not contacts:
            note(f"No people listed yet for {company.name}")
            return [], []

        note(f"Found {len(contacts)} people at {company.name}")
        profiles: list[ContactProfile] = []
        top_company = sorted(
            company_evidence or [],
            key=lambda item: getattr(item, "relevance", 0),
            reverse=True,
        )[:4]
        for contact in contacts:
            person_evidence = self.analyzer.research_agent.lookup_person(
                full_name=contact.full_name,
                company_name=company.name,
                title=contact.title,
                research_goal=(
                    f"Find public facts about {contact.full_name}, "
                    f"{contact.title} at {company.name}, that help a "
                    f"salesperson brief this contact."
                ),
                on_progress=note,
            )
            profiles.append(
                self.contact_profiler.generate(
                    contact=contact,
                    company=company,
                    company_profile=company_profile,
                    products=products,
                    evidence=list(person_evidence) + list(top_company),
                    on_progress=note,
                )
            )
        return contacts, profiles


def save_run(result: PipelineResult) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = RUNS_DIR / stamp
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "user.json").write_text(
        result.user.model_dump_json(indent=2),
        encoding="utf-8",
    )
    (folder / "products.json").write_text(
        json.dumps(
            [product.model_dump() for product in result.products],
            indent=2,
        ),
        encoding="utf-8",
    )
    (folder / "companies.json").write_text(
        json.dumps(
            [company.model_dump() for company in result.companies],
            indent=2,
        ),
        encoding="utf-8",
    )
    (folder / "company_profiles.json").write_text(
        json.dumps(
            [profile.model_dump() for profile in result.company_profiles],
            indent=2,
        ),
        encoding="utf-8",
    )
    (folder / "contacts.json").write_text(
        json.dumps(
            [contact.model_dump() for contact in result.contacts],
            indent=2,
        ),
        encoding="utf-8",
    )
    (folder / "contact_profiles.json").write_text(
        json.dumps(
            [profile.model_dump() for profile in result.contact_profiles],
            indent=2,
        ),
        encoding="utf-8",
    )
    return folder


def _prompt(label: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    if value:
        return value
    if default:
        return default
    raise ValueError(f"{label} is required.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Onboard a seller from a website, upload prospects, "
            "then run ProspectIQ.analyze() for each company."
        )
    )
    parser.add_argument("--name")
    parser.add_argument("--phone")
    parser.add_argument("--email")
    parser.add_argument("--outreach-email")
    parser.add_argument("--website")
    parser.add_argument("--title")
    parser.add_argument("--industry")
    parser.add_argument("--prospects", help="CSV with company_name,website,notes")
    args = parser.parse_args()

    full_name = args.name or _prompt("Your name")
    phone = args.phone or _prompt("Phone")
    email = args.email or _prompt("Email")
    outreach_email = args.outreach_email or email
    website = args.website or _prompt("Company website")
    industry = args.industry or _prompt("Industry")
    title = args.title or _prompt("Title")
    prospects_csv = args.prospects or _prompt(
        "Prospect CSV path",
        "data/uploads/sample_prospects.csv",
    )

    SellerPipeline().run(
        full_name=full_name,
        phone=phone,
        email=email,
        outreach_email=outreach_email,
        website=website,
        prospects_csv=prospects_csv,
        title=title,
        industry=industry,
    )


if __name__ == "__main__":
    main()
