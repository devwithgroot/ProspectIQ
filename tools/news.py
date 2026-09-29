import os
import re

from dotenv import load_dotenv
from tavily import TavilyClient

from config.schemas import News
from tools.base import BaseTool
from tools.news_extractor import NewsExtractor
from tools.news_relevance import NewsRelevance


load_dotenv()


class NewsTool(BaseTool):

    name = "news"

    description = (
        "Find recent company news and extract "
        "source-grounded structured information."
    )

    def __init__(self):

        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not configured."
            )

        self.client = TavilyClient(
            api_key=api_key
        )

        self.relevance = NewsRelevance()
        self.extractor = NewsExtractor()

    def execute(
        self,
        company_name: str,
        max_results: int = 10,
        days: int = 30,
    ) -> list[News]:

        company_name = company_name.strip()

        if not company_name:
            raise ValueError(
                "Company name cannot be empty."
            )

        print("[1/5] Searching recent company news...")

        candidates = self._search_news(
            company_name,
            days,
        )

        print(
            f"[2/5] Candidates retrieved: "
            f"{len(candidates)}"
        )

        if not candidates:
            return []

        print("[3/5] Filtering irrelevant articles...")

        relevant = self.relevance.filter(
            company_name=company_name,
            articles=candidates,
        )

        relevant = relevant[:max_results]

        print(
            f"[3/5] Relevant articles: "
            f"{len(relevant)}"
        )

        if not relevant:
            return []

        print("[4/5] Extracting verified details...")

        news = self.extractor.extract(
            company_name=company_name,
            articles=relevant,
        )

        print("[5/5] News extraction completed.")

        return news

    def _search_news(
        self,
        company_name: str,
        days: int,
    ) -> list[dict]:

        response = self.client.search(
            query=f'"{company_name}" company news',
            topic="news",
            search_depth="advanced",
            max_results=10,
            days=days,
            include_raw_content=False,
        )

        articles = []

        for result in response.get("results", []):

            if not result.get("title"):
                continue

            if not result.get("url"):
                continue

            articles.append(
                self._prepare_article(result)
            )

        return articles

    @staticmethod
    def _prepare_article(
        result: dict,
    ) -> dict:

        url = result["url"]

        return {
            "title": result["title"].strip(),
            "url": url,
            "source": NewsTool._extract_source(url),
            "published_at": result.get(
                "published_date"
            ),
            "content": result.get(
                "content",
                "",
            ).strip(),
        }

    @staticmethod
    def _extract_source(
        url: str,
    ) -> str | None:

        match = re.search(
            r"https?://(?:www\.)?([^/]+)",
            url,
        )

        return (
            match.group(1)
            if match
            else None
        )