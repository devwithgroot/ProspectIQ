from typing import Any

import requests
from pydantic import BaseModel, Field

from tools.base import BaseTool


class CompanyData(BaseModel):
    """
    Structured company information returned by the company data tool.
    """

    company_name: str
    website: str | None = None
    description: str | None = None
    industry: str | None = None
    employee_count: int | None = Field(
        default=None,
        ge=0,
    )
    headquarters: str | None = None
    founded_year: int | None = Field(
        default=None,
        ge=1000,
        le=2100,
    )


class CompanyDataTool(BaseTool):
    """
    Retrieve structured public company information.

    The provider implementation is intentionally isolated from the
    rest of ProspectIQ so that it can be replaced later without
    changing the agents.
    """

    name = "company_data"

    description = (
        "Retrieve structured public information about a company, "
        "including its industry, website, employee count, "
        "headquarters, founding year, and description."
    )

    DEFAULT_TIMEOUT = 10

    def __init__(
        self,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:

        if timeout <= 0:
            raise ValueError(
                "Timeout must be greater than zero"
            )

        self.timeout = timeout

    def execute(
        self,
        company_name: str,
        **kwargs: Any,
    ) -> CompanyData:

        company_name = self._validate_company_name(
            company_name
        )

        # Provider integration will be added here.
        #
        # For now, return a controlled failure rather than
        # silently returning fabricated company information.

        raise NotImplementedError(
            "Company data provider is not configured yet."
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