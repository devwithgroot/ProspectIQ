from config.schemas import Evidence


def main():
    evidence = Evidence(
        title="Asian Paints expansion",
        url="https://example.com/article",
        content="Asian Paints announced a new manufacturing investment.",
        source="Example News",
        relevance=0.91,
        evidence_type="news",
    )

    print("Evidence object:")
    print(evidence.model_dump_json(indent=2))


if __name__ == "__main__":
    main()