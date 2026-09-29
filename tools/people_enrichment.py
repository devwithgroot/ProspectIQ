from typing import Any

from tools.base import BaseTool
from tools.providers.prospeo_enrichment import (
    ProspeoEnrichmentProvider,
)
from config.schemas import PersonData


class PeopleEnrichmentTool(BaseTool):

    name = "people_enrichment"

    description = (
        "Enrich a previously identified person with "
        "verified business contact information."
    )

    def __init__(self) -> None:
        self.provider = ProspeoEnrichmentProvider()

    def execute(
        self,
        person_id: str,
        enrich_mobile: bool = True,
        only_verified_email: bool = False,
        only_verified_mobile: bool = False,
        **kwargs: Any,
    ) -> PersonData:

        return self.provider.enrich_person(
            person_id=person_id,
            enrich_mobile=enrich_mobile,
            only_verified_email=only_verified_email,
            only_verified_mobile=only_verified_mobile,
        )