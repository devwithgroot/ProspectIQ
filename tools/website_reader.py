from typing import Any

import requests
from bs4 import BeautifulSoup

from config.schemas import WebsiteContent
from tools.base import BaseTool


class WebsiteReaderTool(BaseTool):
    """
    Fetch and extract readable text from a public webpage.
    """

    name = "website_reader"

    description = (
        "Fetch a public webpage and extract its readable text, title, "
        "and metadata for company and sales research."
    )

    DEFAULT_TIMEOUT = 10
    MAX_CONTENT_LENGTH = 2_000_000

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

        self.timeout = timeout

    def execute(
        self,
        url: str,
        **kwargs: Any,
    ) -> WebsiteContent:

        url = self._validate_url(url)

        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 "
                        "(compatible; ProspectIQ/1.0)"
                    )
                },
                allow_redirects=True,
            )

            response.raise_for_status()

        except requests.Timeout as exc:
            raise RuntimeError(
                f"Website request timed out: {url}"
            ) from exc

        except requests.HTTPError as exc:
            status_code = (
                exc.response.status_code
                if exc.response is not None
                else "unknown"
            )

            raise RuntimeError(
                f"Website returned HTTP {status_code}: {url}"
            ) from exc

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Failed to fetch website: {url}"
            ) from exc

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        if "text/html" not in content_type:
            raise ValueError(
                f"Unsupported content type: {content_type}"
            )

        if len(response.content) > self.MAX_CONTENT_LENGTH:
            raise ValueError(
                "Website response is too large to process"
            )

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        title = self._extract_title(soup)

        self._remove_non_content_elements(soup)

        content = self._extract_readable_text(soup)

        return WebsiteContent(
            url=response.url,
            title=title,
            content=content,
            status_code=response.status_code,
            content_type=content_type,
        )

    @staticmethod
    def _validate_url(url: str) -> str:
        if not url or not url.strip():
            raise ValueError("URL is required")

        url = url.strip()

        if not url.startswith(
            ("http://", "https://")
        ):
            raise ValueError(
                "URL must start with http:// or https://"
            )

        return url

    @staticmethod
    def _extract_title(
        soup: BeautifulSoup,
    ) -> str:

        if soup.title:
            return soup.title.get_text(
                strip=True
            )

        return ""

    @staticmethod
    def _remove_non_content_elements(
        soup: BeautifulSoup,
    ) -> None:

        for element in soup.find_all(
            [
                "script",
                "style",
                "noscript",
                "svg",
                "iframe",
                "canvas",
                "nav",
                "footer",
                "form",
            ]
        ):
            element.decompose()

    @staticmethod
    def _extract_readable_text(
        soup: BeautifulSoup,
    ) -> str:

        content_root = (
            soup.find("main")
            or soup.find("article")
            or soup.body
            or soup
        )

        text_parts = []

        for element in content_root.find_all(
            [
                "h1",
                "h2",
                "h3",
                "h4",
                "h5",
                "p",
                "li",
            ]
        ):
            text = element.get_text(
                " ",
                strip=True,
            )

            if not text:
                continue

            if len(text) < 2:
                continue

            text_parts.append(text)

        return "\n".join(
            dict.fromkeys(text_parts)
        )