from tools.web_search import WebSearchTool


def main():
    tool = WebSearchTool()

    print("Tool:")
    print(tool.name)

    print("\nDescription:")
    print(tool.description)

    print("\nSearching...\n")

    results = tool.execute(
        query="Asian Paints company expansion India",
        max_results=3,
    )

    for index, result in enumerate(results, start=1):
        print(f"--- Result {index} ---")
        print(f"Title: {result.title}")
        print(f"URL: {result.url}")
        print(f"Source: {result.source}")
        print(f"Type: {result.evidence_type}")
        print(f"Content: {result.content}")
        print(f"Relevance: {result.relevance}")
        print()


if __name__ == "__main__":
    main()