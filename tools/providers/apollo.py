import os
from typing import Any

import requests
from dotenv import load_dotenv

from config.schemas import CompanyData, PersonData


load_dotenv()


class ApolloProvider:
    """
    Apollo API provider for company and people data.

    This class contains Apollo-specific API logic.
    The rest of ProspectIQ should not depend directly
    on Apollo's API response format.
    """

    BASE_URL = "https://api.apollo.io/api/v1"

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

        self.api_key = os.getenv(
            "APOLLO_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "APOLLO_API_KEY is not configured"
            )

        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        }

    def enrich_company(
        self,
        company_name: str,
        domain: str | None = None,
        website: str | None = None,
        linkedin_url: str | None = None,
    ) -> CompanyData:

        params: dict[str, Any] = {}

        if company_name:
            params["name"] = company_name

        if domain:
            params["domain"] = domain

        if website:
            params["website"] = website

        if linkedin_url:
            params["linkedin_url"] = linkedin_url

        response = self._request(
            method="GET",
            endpoint="/organizations/enrich",
            params=params,
        )

        organization = response.get(
            "organization"
        )

        if not organization:
            raise RuntimeError(
                f"Apollo could not find company: "
                f"{company_name}"
            )

        return self._parse_company(
            organization
        )

    def search_people(
        self,
        company_name: str | None = None,
        titles: list[str] | None = None,
        locations: list[str] | None = None,
        limit: int = 10,
    ) -> list[PersonData]:

        params: dict[str, Any] = {
            "per_page": min(limit, 100),
        }

        if company_name:
            params[
                "organization_name"
            ] = company_name

        if titles:
            params[
                "person_titles"
            ] = titles

        if locations:
            params[
                "person_locations"
            ] = locations

        response = self._request(
            method="POST",
            endpoint="/mixed_people/api_search",
            params=params,
        )

        people = response.get(
            "people",
            []
        )

        return [
            self._parse_person(person)
            for person in people
        ]

    def enrich_person(
        self,
        name: str | None = None,
        email: str | None = None,
        domain: str | None = None,
        linkedin_url: str | None = None,
    ) -> PersonData:

        params: dict[str, Any] = {
            "reveal_personal_emails": "false",
            "reveal_phone_number": "false",
        }

        if name:
            params["name"] = name

        if email:
            params["email"] = email

        if domain:
            params["domain"] = domain

        if linkedin_url:
            params["linkedin_url"] = linkedin_url

        response = self._request(
            method="POST",
            endpoint="/people/match",
            params=params,
        )

        person = response.get("person")

        if not person:
            raise RuntimeError(
                "Apollo could not match the person."
            )

        return self._parse_person(person)

    def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any],
    ) -> dict:

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.Timeout as exc:
            raise RuntimeError(
                "Apollo API request timed out."
            ) from exc

        except requests.HTTPError as exc:

            status_code = (
                exc.response.status_code
                if exc.response is not None
                else "unknown"
            )

            try:
                error_data = exc.response.json()
            except Exception:
                error_data = {}

            raise RuntimeError(
                f"Apollo API returned HTTP "
                f"{status_code}: {error_data}"
            ) from exc

        except requests.RequestException as exc:
            raise RuntimeError(
                "Failed to communicate with Apollo API."
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(
                "Apollo returned an invalid JSON response."
            ) from exc

    @staticmethod
    def _parse_company(
        data: dict,
    ) -> CompanyData:

        primary_phone = data.get(
            "primary_phone"
        ) or {}

        headquarters = None

        if data.get("raw_address"):
            headquarters = data.get(
                "raw_address"
            )
        elif data.get("city"):
            headquarters = ", ".join(
                value
                for value in [
                    data.get("city"),
                    data.get("state"),
                    data.get("country"),
                ]
                if value
            )

        return CompanyData(
            id=data.get("id"),
            company_name=data.get(
                "name",
                "",
            ),
            website=data.get(
                "website_url"
            ),
            linkedin_url=data.get(
                "linkedin_url"
            ),
            description=data.get(
                "short_description"
            )
            or data.get(
                "description"
            ),
            industry=data.get(
                "industry"
            ),
            employee_count=data.get(
                "estimated_num_employees"
            ),
            employee_growth_6m=data.get(
                "organization_headcount_six_month_growth"
            ),
            employee_growth_12m=data.get(
                "organization_headcount_twelve_month_growth"
            ),
            employee_growth_24m=data.get(
                "organization_headcount_twenty_four_month_growth"
            ),
            annual_revenue=data.get(
                "annual_revenue"
            ),
            total_funding=data.get(
                "total_funding"
            ),
            latest_funding_stage=data.get(
                "latest_funding_stage"
            ),
            latest_funding_date=data.get(
                "latest_funding_round_date"
            ),
            founded_year=data.get(
                "founded_year"
            ),
            headquarters=headquarters,
            technologies=data.get(
                "technology_names",
                [],
            ),
        )

    @staticmethod
    def _parse_person(
        data: dict,
    ) -> PersonData:

        organization = (
            data.get("organization")
            or {}
        )

        return PersonData(
            id=data.get("id"),
            first_name=data.get(
                "first_name"
            ),
            last_name=data.get(
                "last_name"
            ),
            name=data.get(
                "name"
            ),
            title=data.get(
                "title"
            ),
            email=data.get(
                "email"
            ),
            email_status=data.get(
                "email_status"
            ),
            linkedin_url=data.get(
                "linkedin_url"
            ),
            organization_name=(
                data.get(
                    "organization_name"
                )
                or organization.get(
                    "name"
                )
            ),
            organization_id=(
                data.get(
                    "organization_id"
                )
                or organization.get(
                    "id"
                )
            ),
            city=data.get(
                "city"
            ),
            state=data.get(
                "state"
            ),
            country=data.get(
                "country"
            ),
            seniority=data.get(
                "seniority"
            ),
            departments=data.get(
                "departments",
                [],
            ),
        )