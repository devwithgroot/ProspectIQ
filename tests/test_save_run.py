from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.pipeline import PipelineResult, run_folder_name, save_run
from data.loader import load_mock_bundle


def main():
    print("\n==============================")
    print("SAVE RUN FOLDER NAME TEST")
    print("==============================")

    now = datetime(2026, 9, 26, 1, 30, 0, tzinfo=timezone.utc)
    named = run_folder_name(now=now, git_parts=("feat/excon", "20b76a7", False))
    assert named == "20260926T013000Z-feat-excon-20b76a7"
    print(named)

    dirty = run_folder_name(now=now, git_parts=("feat/excon", "20b76a7", True))
    assert dirty == "20260926T013000Z-feat-excon-20b76a7-dirty"
    print(dirty)

    stamp_only = run_folder_name(now=now, git_parts=("", "", False))
    assert stamp_only == "20260926T013000Z"
    print("git missing falls back to stamp")

    bundle = load_mock_bundle()
    result = PipelineResult(
        user=bundle.user,
        products=bundle.products[:1],
        uploaded=[],
        companies=bundle.companies[:1],
        company_profiles=bundle.company_profiles[:1],
        contacts=[],
        contact_profiles=[],
    )
    with TemporaryDirectory() as tmp:
        folder = Path(tmp)
        with patch("app.pipeline.RUNS_DIR", folder), patch(
            "app.pipeline.run_folder_name",
            return_value="20260926T013000Z-feat-excon-20b76a7",
        ):
            saved = save_run(result)
        assert saved.name == "20260926T013000Z-feat-excon-20b76a7"
        assert (saved / "user.json").exists()
        assert (saved / "companies.json").exists()
        print(f"saved → {saved.name}")

    print("\nSAVE RUN FOLDER NAME TEST PASSED")


if __name__ == "__main__":
    main()
