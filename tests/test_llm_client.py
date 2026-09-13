from llm.client import LLMClient


def main():
    llm = LLMClient()

    response = llm.generate(
        "You are a B2B sales intelligence analyst. "
        "Explain in 5 bullet points what makes a company "
        "a high-value sales prospect."
    )

    print("\n--- MODEL RESPONSE ---\n")
    print(response)


if __name__ == "__main__":
    main()