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
    assert len(result.company_profiles) == 2
    assert len(result.companies) == 2

    for company, profile in zip(result.companies, result.company_profiles):
        print(
            f"{company.name}: "
            f"{profile.overall_score:.1f} / {profile.recommendation}"
        )
        assert company.name
        assert profile.executive_summary
        assert 0 <= profile.overall_score <= 100
        assert company.company_id == profile.company_id

    print("\nPIPELINE ORCHESTRATOR TEST PASSED")


if __name__ == "__main__":
    main()
