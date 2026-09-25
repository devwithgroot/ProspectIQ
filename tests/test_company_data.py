from tools.company_data import CompanyDataTool


def main():
    print("=" * 60)
    print("COMPANY DATA TOOL TEST")
    print("=" * 60)

    tool = CompanyDataTool()

    print(f"\nName: {tool.name}")
    print(f"Description: {tool.description}")

    print("\nTesting validation...")

    try:
        tool.execute(
            company_name=""
        )

    except ValueError as exc:
        print(f"Validation passed: {exc}")

    print("\nTesting provider state...")

    try:
        tool.execute(
            company_name="Asian Paints"
        )

    except NotImplementedError as exc:
        print(f"Provider not configured: {exc}")

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()