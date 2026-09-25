import os
from typing import Any

import requests
from dotenv import load_dotenv

from config.schemas import PersonData


load_dotenv()


class ProspeoProvider:
    """
    Prospeo API provider for people search.
    """

    BASE_URL = "https://api.prospeo.io"
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
            "PROSPEO_API_KEY"
        )

        if not self.api_key:
            raise ValueError(
                "PROSPEO_API_KEY is not configured"
            )

        self.headers = {
            "X-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def search_people(
        self,
        company: str | None = None,
        title: str | None = None,
        location: str | None = None,
        limit: int = 25,
    ) -> list[PersonData]:

        filters: dict[str, Any] = {}

        if company:
            filters["company"] = {
                "names": {
                    "include": [company]
                }
            }

        if title:
            filters["person_job_title"] = {
                "include": [title],
                "match_mode": "CONTAINS",
            }

        if location:
            filters["person_location_search"] = {
                "include": [location]
            }

        payload = {
            "page": 1,
            "filters": filters,
        }

        response = self._request(
            endpoint="/search-person",
            payload=payload,
        )

        results = response.get(
            "results",
            []
        )

        people = []

        for result in results[:limit]:

            person = result.get(
                "person",
                {}
            )

            company_data = result.get(
                "company",
                {}
            )

            people.append(
                self._parse_person(
                    person=person,
                    company=company_data,
                )
            )

        return people

    def _request(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict:

        url = f"{self.BASE_URL}{endpoint}"

        try:
            response = requests.post(
                url,
                headers=self.headers,
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

        except requests.Timeout as exc:
            raise RuntimeError(
                "Prospeo API request timed out."
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
                f"Prospeo API returned HTTP "
                f"{status_code}: {error_data}"
            ) from exc

        except requests.RequestException as exc:
            raise RuntimeError(
                "Failed to communicate with Prospeo API."
            ) from exc

        try:
            return response.json()

        except ValueError as exc:
            raise RuntimeError(
                "Prospeo returned invalid JSON."
            ) from exc

    @staticmethod
    def _parse_person(
        person: dict,
        company: dict,
    ) -> PersonData:

        # ---------------------------------
        # Basic person information
        # ---------------------------------

        person_id = person.get(
            "person_id"
        )

        first_name = person.get(
            "first_name"
        )

        last_name = person.get(
            "last_name"
        )

        full_name = person.get(
            "full_name"
        )

        linkedin_url = person.get(
            "linkedin_url"
        )

        # ---------------------------------
        # Current job information
        # ---------------------------------

        current_job_title = person.get(
            "current_job_title"
        )

        job_history = person.get(
            "job_history",
            []
        )

        current_job = {}

        if isinstance(job_history, list):

            for job in job_history:

                if job.get("current") is True:
                    current_job = job
                    break

            if not current_job and job_history:
                current_job = job_history[0]

        seniority = current_job.get(
            "seniority"
        )

        departments = current_job.get(
            "departments",
            []
        )

        # ---------------------------------
        # Email
        # ---------------------------------

        email_data = person.get(
            "email"
        )

        email = None
        email_status = None

        if isinstance(email_data, dict):

            email = email_data.get(
                "email"
            )

            email_status = email_data.get(
                "status"
            )

        elif isinstance(email_data, str):

            email = email_data

        # ---------------------------------
        # Location
        # ---------------------------------

        location = person.get(
            "location",
            {}
        )

        if not isinstance(location, dict):
            location = {}

        city = location.get(
            "city"
        )

        state = location.get(
            "state"
        )

        country = location.get(
            "country"
        )

        # ---------------------------------
        # Company
        # ---------------------------------

        organization_id = company.get(
            "company_id"
        )

        organization_name = company.get(
            "name"
        )

        # ---------------------------------
        # Build normalized model
        # ---------------------------------

        return PersonData(
            id=person_id,

            first_name=first_name,

            last_name=last_name,

            name=full_name,

            title=current_job_title,

            email=email,

            email_status=email_status,

            linkedin_url=linkedin_url,

            organization_name=organization_name,

            organization_id=organization_id,

            city=city,

            state=state,

            country=country,

            seniority=seniority,

            departments=departments,
        )