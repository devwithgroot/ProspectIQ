import os
from typing import Any

import requests
from dotenv import load_dotenv

from config.schemas import PersonData

load_dotenv()


class ProspeoEnrichmentProvider:
    """
    Provider responsible for enriching an existing Prospeo person
    with contact information such as verified email and mobile.
    """

    BASE_URL = "https://api.prospeo.io"
    DEFAULT_TIMEOUT = 10

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        if timeout <= 0:
            raise ValueError("Timeout must be greater than zero")

        self.timeout = timeout

        self.api_key = os.getenv("PROSPEO_API_KEY")

        if not self.api_key:
            raise ValueError("PROSPEO_API_KEY is not configured")

        self.headers = {
            "X-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def enrich_person(
        self,
        person_id: str,
        enrich_mobile: bool = True,
        only_verified_email: bool = False,
        only_verified_mobile: bool = False,
    ) -> PersonData:

        if not person_id or not person_id.strip():
            raise ValueError("person_id is required")

        payload: dict[str, Any] = {
            "data": {
                "person_id": person_id.strip(),
            },
            "enrich_mobile": enrich_mobile,
            "only_verified_email": only_verified_email,
            "only_verified_mobile": only_verified_mobile,
        }

        response = self._request(
            endpoint="/enrich-person",
            payload=payload,
        )

        if response.get("error"):
            error_code = response.get("error_code", "UNKNOWN_ERROR")

            raise RuntimeError(
                f"Prospeo enrichment failed: {error_code}"
            )

        person = response.get("person", {})
        company = response.get("company", {}) or {}

        return self._parse_person(
            person=person,
            company=company,
        )

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
                f"Prospeo API returned HTTP {status_code}: "
                f"{error_data}"
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

        email_data = person.get("email") or {}

        mobile_data = person.get("mobile") or {}

        location = person.get("location") or {}

        job_history = person.get("job_history") or []

        current_job = {}

        if isinstance(job_history, list):

            for job in job_history:

                if job.get("current") is True:
                    current_job = job
                    break

            if not current_job and job_history:
                current_job = job_history[0]

        departments = current_job.get("departments", [])

        if not isinstance(departments, list):
            departments = []

        return PersonData(
            id=person.get("person_id"),

            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            name=person.get("full_name"),

            title=person.get("current_job_title"),

            email=email_data.get("email"),
            email_status=email_data.get("status"),

            mobile=mobile_data.get("mobile"),
            mobile_status=mobile_data.get("status"),

            linkedin_url=person.get("linkedin_url"),

            organization_name=company.get("name"),
            organization_id=company.get("company_id"),

            city=location.get("city"),
            state=location.get("state"),
            country=location.get("country"),

            seniority=current_job.get("seniority"),
            departments=departments,
        )