from typing import Any

from config.research_log import get_logger
from config.schemas import PersonData
from tools.base import BaseTool
from tools.providers.prospeo import ProspeoProvider

log = get_logger("people")


class PeopleDataTool(BaseTool):
    """
    ProspectIQ people-data tool.

    Prospeo is currently used as the underlying provider.
    """

    name = "people_data"

    description = (
        "Search for relevant people and decision makers "
        "within companies using company, title, and location."
    )

    def __init__(
        self,
        provider: ProspeoProvider | None = None,
    ) -> None:

        self.provider = (
            provider
            if provider is not None
            else ProspeoProvider()
        )

    def execute(
        self,
        company: str | None = None,
        title: str | None = None,
        location: str | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> list[PersonData]:

        if not company and not title and not location:
            raise ValueError(
                "At least one search parameter is required."
            )

        log.info(
            "People search company=%r title=%r location=%r limit=%s",
            company,
            title,
            location,
            limit,
        )
        try:
            people = self.provider.search_people(
                company=company,
                title=title,
                location=location,
                limit=limit,
            )
        except Exception:
            log.exception("People search failed company=%r", company)
            raise
        log.info("People search ok count=%s", len(people))
        return people