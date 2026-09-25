from tools.website_reader import WebsiteReaderTool


def main():
    tool = WebsiteReaderTool()

    print("=" * 60)
    print("WEBSITE READER TOOL TEST")
    print("=" * 60)

    print(f"\nName: {tool.name}")
    print(f"Description: {tool.description}")

    print("\nReading website...")

    result = tool.execute(
        url="https://www.asianpaints.com/"
    )

    print("\n" + "-" * 60)
    print("RESULT")
    print("-" * 60)

    print(f"Type: {type(result).__name__}")
    print(f"Title: {result.title}")
    print(f"URL: {result.url}")
    print(f"Status Code: {result.status_code}")
    print(f"Content Type: {result.content_type}")

    print("\nContent preview:")
    print("-" * 60)
    print(result.content[:5000])

    print("\n" + "=" * 60)
    print("TEST COMPLETED")
    print("=" * 60)


if __name__ == "__main__":
    main()