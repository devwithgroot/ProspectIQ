import json

from llm.client import LLMClient


class NewsRelevance:

    def __init__(self):
        self.llm = LLMClient()

    def filter(
        self,
        company_name: str,
        articles: list[dict],
    ) -> list[dict]:

        if not articles:
            return []

        prompt = self._build_prompt(
            company_name,
            articles,
        )

        response = self.llm.generate(
            prompt=prompt,
            temperature=0,
            max_tokens=1000,
        )

        results = json.loads(response)

        relevant_urls = {
            item["url"]
            for item in results
            if item.get("relevant") is True
        }

        return [
            article
            for article in articles
            if article["url"] in relevant_urls
        ]

    @staticmethod
    def _build_prompt(
        company_name: str,
        articles: list[dict],
    ) -> str:

        return f"""
You are a strict news relevance classifier.

Target company:
{company_name}

Determine whether each article is genuine recent news ABOUT the target company.

Relevant:
- Company announcements
- Acquisitions
- Investments
- Partnerships
- Product launches
- Technology developments
- Leadership changes
- Financial/business developments
- Regulatory developments involving the company
- Major operational developments

NOT relevant:
- Stock forecast pages
- Stock prediction pages
- Generic market commentary
- Pages that only mention the company
- Investment recommendation pages
- Price-target pages
- Unrelated articles
- Duplicate versions of the same story

Do not infer relevance.

Return ONLY JSON:

[
  {{
    "url": "article URL",
    "relevant": true
  }}
]

Articles:

{json.dumps(articles, ensure_ascii=False)}
""".strip()