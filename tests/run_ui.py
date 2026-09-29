import sys
import traceback

from tests.test_api import main as test_api
from tests.test_catalog import main as test_catalog
from tests.test_email_verify import main as test_email_verify
from tests.test_prospect_upload import main as test_prospect_upload
from tests.test_outreach import main as test_outreach
from tests.test_research_jobs import main as test_research_jobs


TESTS = [
    ("prospect upload", test_prospect_upload),
    ("catalog", test_catalog),
    ("email verify", test_email_verify),
    ("api", test_api),
    ("research jobs", test_research_jobs),
    ("outreach draft", test_outreach),
]


def main():
    print("\n==============================")
    print("API TEST RUNNER")
    print("==============================")

    for name, test in TESTS:
        print(f"\n>>> {name}")
        try:
            test()
        except Exception:
            traceback.print_exc()
            print(f"\nFAILED: {name}")
            return 1

    print("\n==============================")
    print("API TESTS PASSED")
    print("==============================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
