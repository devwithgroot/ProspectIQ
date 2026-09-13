from typing import Any

from tools.base import BaseTool


class MockSearchTool(BaseTool):
    name = "mock_search"

    description = (
        "Mock search tool used during development "
        "to simulate web search results."
    )

    def execute(self, query: str, **kwargs: Any) -> list[dict]:
        return [
            {
                "title": "Example Company Expansion",
                "url": "https://example.com/news/expansion",
                "snippet": (
                    f"Example search result related to: {query}"
                ),
                "source": "Mock Search",
            }
        ]