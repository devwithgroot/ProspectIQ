import sys
import traceback

from tests.test_connectors import main as test_connectors
from tests.test_excon import main as test_excon
from tests.test_json_util import main as test_json_util
from tests.test_mock_data import main as test_mock_data
from tests.test_outreach_agent import main as test_outreach_agent
from tests.test_outreach_schemas import main as test_outreach_schemas


TESTS = [
    ("mock data", test_mock_data),
    ("schemas", test_outreach_schemas),
    ("json parse", test_json_util),
    ("connectors", test_connectors),
    ("outreach agent (LLM)", test_outreach_agent),
    ("excon (LLM)", test_excon),
]


def main():
    print("\n==============================")
    print("EXCON TEST RUNNER")
    print("==============================")

    failed = []

    for name, test in TESTS:
        print(f"\n>>> {name}")
        try:
            test()
        except Exception:
            traceback.print_exc()
            failed.append(name)
            print(f"\nFAILED: {name}")
            break

    print("\n==============================")
    if failed:
        print(f"EXCON TESTS FAILED: {failed[0]}")
        print("==============================")
        return 1

    print("EXCON TESTS PASSED")
    print("==============================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
