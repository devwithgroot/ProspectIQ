from tools.news import NewsTool


def main():

    print("=" * 70)
    print("PROSPECTIQ NEWS TOOL TEST")
    print("=" * 70)

    company_name = input("Enter company name: ").strip()

    print(f"\nSearching recent news for: {company_name}\n")

    tool = NewsTool()

    news = tool.execute(
        company_name=company_name,
        max_results=10,
        days=30,
    )

    print("=" * 70)
    print(f"News articles found: {len(news)}")
    print("=" * 70)

    for index, article in enumerate(news, start=1):

        print(f"\n{'=' * 70}")
        print(f"NEWS {index}")
        print(f"{'=' * 70}")

        print(f"Title         : {article.title}")
        print(f"Source        : {article.source}")
        print(f"Published At  : {article.published_at}")
        print(f"URL           : {article.url}")

        print("\nSUMMARY")
        print("-" * 70)
        print(article.summary or "Not available")

        print("\nKEY FACTS")
        print("-" * 70)

        if article.key_facts:
            for fact in article.key_facts:
                print(f"- {fact}")
        else:
            print("Not available")

        print("\nPEOPLE")
        print("-" * 70)
        print(
            ", ".join(article.people_mentioned)
            if article.people_mentioned
            else "Not available"
        )

        print("\nORGANIZATIONS")
        print("-" * 70)
        print(
            ", ".join(article.organizations_mentioned)
            if article.organizations_mentioned
            else "Not available"
        )

        print("\nPRODUCTS")
        print("-" * 70)
        print(
            ", ".join(article.products_mentioned)
            if article.products_mentioned
            else "Not available"
        )

        print("\nTECHNOLOGIES")
        print("-" * 70)
        print(
            ", ".join(article.technologies_mentioned)
            if article.technologies_mentioned
            else "Not available"
        )

        print("\nEVENT DATE")
        print("-" * 70)
        print(article.event_date or "Not available")

        print("\nLOCATION")
        print("-" * 70)
        print(article.location or "Not available")

        print("\nEVIDENCE")
        print("-" * 70)

        if article.evidence:
            for evidence in article.evidence:
                print(f"- {evidence}")
        else:
            print("Not available")


if __name__ == "__main__":
    main()