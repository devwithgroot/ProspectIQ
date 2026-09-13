from tools.mock_search import MockSearchTool


def main():
    tool = MockSearchTool()

    print("Tool name:")
    print(tool.name)

    print("\nTool description:")
    print(tool.description)

    print("\nTool result:")

    results = tool.execute(
        query="Asian Paints expansion"
    )

    for result in results:
        print(result)


if __name__ == "__main__":
    main()