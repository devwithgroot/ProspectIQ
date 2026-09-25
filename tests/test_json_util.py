from config.excon_schemas import DraftContent
from llm.json_util import extract_json_text, extract_think, parse_model, reason_lines


def main():
    print("\n==============================")
    print("LLM JSON PARSE TEST")
    print("==============================")

    fenced = """
<think>planning</think>
```json
{
  "channel": "email",
  "subject": "Working session",
  "body": "Hello from the model.",
  "rationale": "Primary channel"
}
```
"""

    parsed = parse_model(DraftContent, fenced)
    assert parsed.channel == "email"
    assert parsed.subject == "Working session"
    assert extract_think(fenced) == "planning"
    assert reason_lines("Need hiring signals. Then check plants.") == [
        "Why: Need hiring signals.",
        "Why: Then check plants.",
    ]
    print(extract_json_text(fenced))
    print("LLM JSON PARSE TEST PASSED")


if __name__ == "__main__":
    main()
