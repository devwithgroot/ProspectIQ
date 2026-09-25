from typing import Any

from config.schemas import CompanyData
from tools.base import BaseTool
from tools.providers.apollo import ApolloProvider


class CompanyDataTool(BaseTool):
    """
    ProspectIQ company data tool.

    The tool exposes a provider-independent interface.
    Apollo is currently used as the underlying provider.
    """

    name = "company_data"

    description = (
        "Retrieve structured public information about a company, "
        "including industry, employees, revenue, funding, "
        "technology, growth, and company metadata."
    )

    def __init__(
        self,
        provider: ApolloProvider | None = None,
    ) -> None:

        self.provider = (
            provider
            if provider is not None
            else ApolloProvider()
        )

    def execute(
        self,
        company_name: str,
        domain: str | None = None,
        website: str | None = None,
        linkedin_url: str | None = None,
        **kwargs: Any,
    ) -> CompanyData:

        company_name = self._validate_company_name(
            company_name
        )

        return self.provider.enrich_company(
            company_name=company_name,
            domain=domain,
            website=website,
            linkedin_url=linkedin_url,
        )

    @staticmethod
    def _validate_company_name(
        company_name: str,
    ) -> str:

        if not company_name or not company_name.strip():
            raise ValueError(
                "Company name is required"
            )

        return company_name.strip()