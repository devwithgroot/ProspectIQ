from pathlib import Path

from app.pipeline import SellerPipeline


def main():
    print("\n==============================")
    print("PIPELINE ORCHESTRATOR TEST")
    print("==============================")

    result = SellerPipeline().run(
        full_name="Priya Mehta",
        phone="+919845512210",
        email="priya.mehta@nexusflow.io",
        website="https://www.zoho.com",
        prospects_csv=Path("data/uploads/sample_prospects.csv"),
        title="Account Executive",
        industry="Software / SaaS",
    )

    names = [row.company_name for row in result.uploaded]
    assert names == ["Asian Paints", "Havells India"]
    assert len(result.reports) == 2
    assert len(result.prospects) == 2

    for report, prospect in zip(result.reports, result.prospects):
        print(
            f"{prospect.company_name}: "
            f"{prospect.overall_score:.1f} / {prospect.recommendation}"
        )
        assert report.company_name
        assert report.executive_summary
        assert 0 <= prospect.overall_score <= 100
        assert len(report.evidence) > 0

    print("\nPIPELINE ORCHESTRATOR TEST PASSED")


if __name__ == "__main__":
    main()
