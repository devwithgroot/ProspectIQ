import os
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient

from tools.base import BaseTool

from config.research_log import get_logger
from config.schemas import Evidence

log = get_logger("tavily")


load_dotenv()


class WebSearchTool(BaseTool):
    name = "web_search"

    description = (
        "Search the public web for information about a company, "
        "industry, market, people, products, events, or recent developments."
    )

    def __init__(self):
        api_key = os.getenv("TAVILY_API_KEY")

        if not api_key:
            raise ValueError(
                "TAVILY_API_KEY is not configured"
            )

        self.client = TavilyClient(api_key=api_key)

    def execute(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> list[dict]:

        log.info("Tavily search query=%r max=%s", query, max_results)
        try:
            response = self.client.search(
                query=query,
                max_results=max_results,
            )
        except Exception:
            log.exception("Tavily search failed query=%r", query)
            raise

        results = []

        for result in response.get("results", []):
            results.append(
                Evidence(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    content=result.get("content", ""),
                    source="web_search",
                    evidence_type="web",
                ))

        log.info("Tavily search ok results=%s", len(results))
        return results