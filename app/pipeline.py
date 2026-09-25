from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from app.onboarding import OnboardingAgent
from app.orchestrator import ProspectIQ
from app.prospect_upload import UploadedProspect, load_prospect_csv
from app.report_mapper import report_to_prospect
from config.excon_schemas import Product, Prospect, User
from config.schemas import ProspectReport


RUNS_DIR = Path(__file__).resolve().parent.parent / "data" / "runs"


class PipelineResult(BaseModel):
    user: User
    products: list[Product]
    uploaded: list[UploadedProspect]
    prospects: list[Prospect]
    reports: list[ProspectReport] = Field(default_factory=list)


class SellerPipeline:
    def __init__(self):
        self.analyzer = ProspectIQ()
        self.onboarder = OnboardingAgent()

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
        reports: list[ProspectReport] = []
        prospects: list[Prospect] = []

        for index, row in enumerate(uploaded, start=1):
            print("\n==============================")
            print(f"ORCHESTRATOR {index}/{len(uploaded)}: {row.company_name}")
            print("==============================")

            research_goal = (
                f"Determine whether {row.company_name} is a high-value "
                f"B2B sales prospect for {user.company.name}, which sells "
                f"{product_names}."
            )

            note(f"Looking into {row.company_name} ({index}/{len(uploaded)})")
            report = self.analyzer.analyze(
                company_name=row.company_name,
                research_goal=research_goal,
                on_progress=note,
            )
            reports.append(report)
            prospects.append(
                report_to_prospect(
                    report=report,
                    uploaded=row,
                    user=user,
                    products=products,
                )
            )
            note(f"Ready with the {row.company_name} briefing")

        note("Putting your briefings together")
        result = PipelineResult(
            user=user,
            products=products,
            uploaded=uploaded,
            prospects=prospects,
            reports=reports,
        )
        saved = save_run(result)
        print(f"\nSaved run to {saved}")
        return result


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
    (folder / "prospects.json").write_text(
        json.dumps(
            [prospect.model_dump() for prospect in result.prospects],
            indent=2,
        ),
        encoding="utf-8",
    )
    (folder / "reports.json").write_text(
        json.dumps(
            [report.model_dump() for report in result.reports],
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
