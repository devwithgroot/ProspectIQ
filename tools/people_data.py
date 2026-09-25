from typing import Any

from config.schemas import PersonData
from tools.base import BaseTool
from tools.providers.prospeo import ProspeoProvider


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

        return self.provider.search_people(
            company=company,
            title=title,
            location=location,
            limit=limit,
        )