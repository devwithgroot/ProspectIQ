from agents.outreach_agent import format_email_body


def main():
    print("\n==============================")
    print("EMAIL BODY FORMAT TEST")
    print("==============================")

    raw = (
        "Hi Pablo, I’m Anish Srivastava, Chief Technology Officer at TezBytes. "
        "We specialize in helping Indian MSMEs improve operational efficiency. "
        "Your company’s focus on career development aligns well with our offerings. "
        "I’d like to suggest a 20-minute working session. "
        "Best regards, Anish Srivastava anishamsri@gmail.com "
        "Reply STOP if you would prefer not to receive emails like this."
    )
    formatted = format_email_body(raw)
    assert formatted.startswith("Hi Pablo,")
    assert "\n\n" in formatted
    assert "Best regards," in formatted
    assert "anishamsri@gmail.com" in formatted
    print(formatted)

    short = format_email_body(
        "Hi Amit — I help teams like Everest Ply cut the manual work. "
        "Would a 15-minute look be useful?"
    )
    assert short.startswith("Hi Amit,")
    assert "\n\n" in short
    print(short)
    print("\nEMAIL BODY FORMAT TEST PASSED")


if __name__ == "__main__":
    main()
