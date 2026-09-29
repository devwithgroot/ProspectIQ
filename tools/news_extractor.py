import json
import re

from config.schemas import News
from llm.client import LLMClient


class NewsExtractor:

    def __init__(self):
        self.llm = LLMClient()

    def extract(
        self,
        company_name: str,
        articles: list[dict],
        batch_size: int = 2,
    ) -> list[News]:

        results = []

        for start in range(0, len(articles), batch_size):

            batch = articles[start:start + batch_size]

            print(
                f"[LLM] Extracting articles "
                f"{start + 1}-{start + len(batch)} "
                f"of {len(articles)}..."
            )

            prompt = self._build_prompt(
                company_name,
                batch,
            )

            response = self.llm.generate(
                prompt=prompt,
                temperature=0,
                max_tokens=1200,
            )

            data = self._parse_response(response)

            for item in data:
                results.append(
                    News(
                        company_name=company_name,
                        **item,
                    )
                )

        return results

    @staticmethod
    def _build_prompt(
        company_name: str,
        articles: list[dict],
    ) -> str:

        payload = json.dumps(
            articles,
            ensure_ascii=False,
            indent=2,
        )

        return f"""
You are a strict source-grounded news extraction system.

Target company:
{company_name}

Extract information ONLY from the supplied article text.

Rules:

1. Never use outside knowledge.
2. Never infer missing information.
3. Never invent names, dates, organizations, products,
   technologies or locations.
4. Keep every article separate.
5. The title, URL, source and published_at must come
   directly from the supplied article metadata.
6. summary must describe only facts explicitly stated
   in the article.
7. key_facts must contain only explicitly stated facts.
8. people_mentioned must contain only people explicitly
   mentioned in the article.
9. organizations_mentioned must contain only organizations
   explicitly mentioned in the article.
10. products_mentioned must contain only products explicitly
    mentioned in the article.
11. technologies_mentioned must contain only technologies
    explicitly mentioned in the article.
12. event_date must contain a date only when the article
    explicitly states the date of the event.
13. location must contain a location only when explicitly
    stated.
14. evidence must contain short factual statements copied
    or closely quoted from the supplied article that support
    the extracted information.
15. If information is unavailable, return null or [].
16. Do not classify the article.
17. Do not add stock predictions or analyst opinions as facts.
18. Return ONLY valid JSON.

Expected format:

[
  {{
    "title": "article title",
    "url": "article URL",
    "source": "source domain",
    "published_at": "publication date or null",

    "summary": "concise factual summary",

    "key_facts": [
      "fact 1",
      "fact 2"
    ],

    "people_mentioned": [],
    "organizations_mentioned": [],
    "products_mentioned": [],
    "technologies_mentioned": [],

    "event_date": null,
    "location": null,

    "evidence": [
      "supporting statement from article"
    ]
  }}
]

Articles:

{payload}
""".strip()

    @staticmethod
    def _parse_response(response: str) -> list[dict]:

        response = response.strip()

        response = re.sub(
            r"^```(?:json)?\s*",
            "",
            response,
            flags=re.IGNORECASE,
        )

        response = re.sub(
            r"\s*```$",
            "",
            response,
        )

        data = json.loads(response)

        if not isinstance(data, list):
            raise ValueError(
                "News extractor returned invalid JSON."
            )

        return data