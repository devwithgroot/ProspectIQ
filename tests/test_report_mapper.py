import json
import unittest
from pathlib import Path

from app.prospect_upload import UploadedProspect
from app.report_mapper import report_to_company
from config.excon_schemas import Product, User
from config.schemas import Evidence, ProspectReport


def _user() -> User:
    return User.model_validate(
        json.loads(Path("data/mock/user.json").read_text(encoding="utf-8"))
    )


def _product() -> Product:
    return Product(
        product_id="pd_test",
        name="Test Product",
        category="Software",
        description="Test",
        icp="Manufacturers",
        target_industries=["Manufacturing"],
        value_props=["Visibility"],
        use_cases=["Planning"],
        differentiators=["Fast"],
        objections=["Price"],
        typical_buyers=["Ops leader"],
        pricing_model="Subscription",
    )


def _report(**overrides) -> ProspectReport:
    base = dict(
        company_name="Acme",
        executive_summary="Summary.",
        prospect_score=72.5,
        recommendation="Potential prospect",
        key_signals=["Cloud hiring is expanding."],
        risks=["Limited evidence."],
        recommended_sales_approach="Lead with cloud.",
        evidence=[
            Evidence(
                title="Cloud program",
                url="https://example.com/cloud",
                content="Acme cloud modernization and engineering hiring continues.",
                source="web_search",
                relevance=0.7,
                quality=0.8,
            )
        ],
    )
    base.update(overrides)
    return ProspectReport(**base)


class ReportMapperEvidenceTests(unittest.TestCase):
    def test_matching_signal_gets_evidence_citation(self):
        report = _report()
        _, profile = report_to_company(
            report=report,
            uploaded=UploadedProspect(company_name="Acme"),
            user=_user(),
            products=[_product()],
        )

        self.assertEqual(len(profile.signals), 1)
        self.assertEqual(
            profile.signals[0].evidence,
            "Cloud program — https://example.com/cloud",
        )
        self.assertIn("https://example.com/cloud", profile.signals[0].evidence or "")

    def test_tie_break_prefers_higher_overlap_then_relevance(self):
        report = _report(
            key_signals=["Cloud hiring modernization push."],
            evidence=[
                Evidence(
                    title="Cloud update",
                    url="https://example.com/a",
                    content="cloud hiring",
                    source="web_search",
                    relevance=0.9,
                    quality=0.9,
                ),
                Evidence(
                    title="Deep cloud hiring modernization",
                    url="https://example.com/b",
                    content="cloud hiring modernization engineering",
                    source="web_search",
                    relevance=0.4,
                    quality=0.4,
                ),
            ],
        )

        _, profile = report_to_company(
            report=report,
            uploaded=UploadedProspect(company_name="Acme"),
            user=_user(),
            products=[_product()],
        )

        self.assertEqual(
            profile.signals[0].evidence,
            "Deep cloud hiring modernization — https://example.com/b",
        )

    def test_tie_break_uses_relevance_when_overlap_equal(self):
        report = _report(
            key_signals=["Cloud hiring teams."],
            evidence=[
                Evidence(
                    title="First cloud hiring",
                    url="https://example.com/first",
                    content="cloud hiring teams",
                    source="web_search",
                    relevance=0.5,
                    quality=0.5,
                ),
                Evidence(
                    title="Second cloud hiring",
                    url="https://example.com/second",
                    content="cloud hiring teams",
                    source="web_search",
                    relevance=0.95,
                    quality=0.5,
                ),
            ],
        )

        _, profile = report_to_company(
            report=report,
            uploaded=UploadedProspect(company_name="Acme"),
            user=_user(),
            products=[_product()],
        )

        self.assertEqual(
            profile.signals[0].evidence,
            "Second cloud hiring — https://example.com/second",
        )

    def test_unrelated_signal_gets_none_evidence(self):
        report = _report(
            key_signals=["Opening fifty offices across EMEA next quarter."],
        )

        _, profile = report_to_company(
            report=report,
            uploaded=UploadedProspect(company_name="Acme"),
            user=_user(),
            products=[_product()],
        )

        self.assertIsNone(profile.signals[0].evidence)

    def test_empty_evidence_list_gets_none_evidence(self):
        report = _report(evidence=[])

        company, profile = report_to_company(
            report=report,
            uploaded=UploadedProspect(company_name="Acme"),
            user=_user(),
            products=[_product()],
        )

        self.assertIsNone(profile.signals[0].evidence)
        self.assertEqual(company.sources, [])

    def test_score_and_recommendation_unchanged(self):
        report = _report(
            prospect_score=88.0,
            recommendation="High-priority prospect",
        )

        _, profile = report_to_company(
            report=report,
            uploaded=UploadedProspect(company_name="Acme"),
            user=_user(),
            products=[_product()],
        )

        self.assertEqual(profile.overall_score, 88.0)
        self.assertEqual(profile.recommendation, "High-priority prospect")


if __name__ == "__main__":
    unittest.main()
