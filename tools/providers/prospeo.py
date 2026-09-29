import os
import re
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()
from config.schemas import PersonData


class ProspeoProvider:
    """
    Prospeo API provider.

    Prospeo is used as a structured people-data source and
    verification/enrichment layer.

    It is NOT treated as the primary source of truth for
    person identity. Public web evidence is collected first.
    """

    BASE_URL = "https://api.prospeo.io"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: int = 30,
    ) -> None:

        self.api_key = (
            api_key
            or os.getenv("PROSPEO_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "PROSPEO_API_KEY is not set."
            )

        self.timeout = timeout

    # =========================================================
    # HTTP
    # =========================================================

    def _request(
        self,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:

        url = f"{self.BASE_URL}/{endpoint}"

        headers = {
            "Content-Type": "application/json",
            "X-KEY": self.api_key,
        }

        response = requests.post(
            url,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        # -----------------------------------------------------
        # NO RESULTS IS NOT A FATAL ERROR
        # -----------------------------------------------------

        if response.status_code == 400:

            try:
                data = response.json()
            except Exception:
                data = {}

            if data.get("error_code") == "NO_RESULTS":
                return {
                    "no_results": True,
                    "data": [],
                }

            raise RuntimeError(
                f"Prospeo API returned HTTP 400: {data}"
            )

        response.raise_for_status()

        try:
            return response.json()
        except Exception as exc:
            raise RuntimeError(
                "Prospeo returned an invalid JSON response."
            ) from exc

    # =========================================================
    # SEARCH PEOPLE BY COMPANY
    # =========================================================

    def search_people(
        self,
        company: str | None = None,
        title: str | None = None,
        location: str | None = None,
        limit: int = 10,
    ) -> list[PersonData]:

        filters: dict[str, Any] = {}

        # -----------------------------------------------------
        # Company
        # -----------------------------------------------------

        if company:

            filters["company"] = {
                "names": {
                    "include": [company]
                }
            }

        # -----------------------------------------------------
        # Title
        # -----------------------------------------------------

        if title:

            filters["job_title"] = {
                "include": [title]
            }

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # Don't blindly send arbitrary location strings to
        # Prospeo. Their location filters use canonical values.
        #
        # For now we omit location rather than causing a
        # malformed request.
        # -----------------------------------------------------

        payload = {
            "page": 1,
            "limit": limit,
            "filters": filters,
        }

        response = self._request(
            "search-person",
            payload,
        )

        if response.get("no_results"):
            return []

        return self._parse_people_response(
            response,
            limit=limit,
        )

    # =========================================================
    # SEARCH ONE PERSON
    # =========================================================

    def search_person(
        self,
        name: str,
        company: str | None = None,
        limit: int = 10,
    ) -> list[PersonData]:

        filters: dict[str, Any] = {}

        # -----------------------------------------------------
        # Person name
        # -----------------------------------------------------

        filters["person"] = {
            "names": {
                "include": [name]
            }
        }

        # -----------------------------------------------------
        # Company
        # -----------------------------------------------------

        if company:

            filters["company"] = {
                "names": {
                    "include": [company]
                }
            }

        payload = {
            "page": 1,
            "limit": limit,
            "filters": filters,
        }

        response = self._request(
            "search-person",
            payload,
        )

        if response.get("no_results"):
            return []

        return self._parse_people_response(
            response,
            limit=limit,
        )

    # =========================================================
    # PARSE RESPONSE
    # =========================================================

    def _parse_people_response(
        self,
        response: dict[str, Any],
        limit: int = 10,
    ) -> list[PersonData]:

        raw_people = []

        # Prospeo response structures can vary.
        # Try common locations.

        if isinstance(
            response.get("results"),
            list,
        ):
            raw_people = response["results"]

        elif isinstance(
            response.get("people"),
            list,
        ):
            raw_people = response["people"]

        elif isinstance(
            response.get("data"),
            list,
        ):
            raw_people = response["data"]

        elif isinstance(
            response.get("data"),
            dict,
        ):

            data = response["data"]

            if isinstance(
                data.get("results"),
                list,
            ):
                raw_people = data["results"]

            elif isinstance(
                data.get("people"),
                list,
            ):
                raw_people = data["people"]

        people: list[PersonData] = []

        for item in raw_people[:limit]:

            if not isinstance(item, dict):
                continue

            person = self._parse_person(item)

            if person:
                people.append(person)

        return people

    # =========================================================
    # PARSE PERSON
    # =========================================================

    def _parse_person(
        self,
        data: dict[str, Any],
    ) -> PersonData | None:

        name = (
            data.get("name")
            or data.get("full_name")
            or data.get("person_name")
        )

        if not name:
            return None

        company = self._extract_company(data)

        title = (
            data.get("title")
            or data.get("job_title")
            or data.get("position")
        )

        location = (
            data.get("location")
            or data.get("city")
        )

        email = (
            data.get("email")
            or data.get("work_email")
        )

        mobile = (
            data.get("mobile")
            or data.get("mobile_number")
            or data.get("phone")
        )

        person_id = (
            data.get("id")
            or data.get("person_id")
            or data.get("person_oid")
        )

        return PersonData(
            name=str(name),
            title=title,
            company=company,
            location=location,
            email=email,
            mobile=mobile,
            prospeo_verified=True,
            prospeo_person_id=person_id,
            data_sources=["prospeo"],
            confidence=0.90,
        )

    # =========================================================
    # COMPANY EXTRACTION
    # =========================================================

    def _extract_company(
        self,
        data: dict[str, Any],
    ) -> str | None:

        company = data.get("company")

        if isinstance(company, str):
            return company

        if isinstance(company, dict):

            return (
                company.get("name")
                or company.get("company_name")
            )

        return (
            data.get("company_name")
            or data.get("organization")
        )

    # =========================================================
    # NORMALIZATION HELPERS
    # =========================================================

    @staticmethod
    def normalize_name(
        value: str,
    ) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"[^a-z0-9\s]",
            " ",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value

    @staticmethod
    def normalize_company(
        value: str,
    ) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"[.,]",
            "",
            value,
        )

        value = re.sub(
            r"\b(private|pvt|limited|ltd|llp|incorporated|inc)\b",
            "",
            value,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        )

        return value.strip()

    # =========================================================
    # MATCH PERSON
    # =========================================================

    def person_matches(
        self,
        web_person: PersonData,
        prospeo_person: PersonData,
        company: str,
    ) -> bool:

        web_name = self.normalize_name(
            web_person.name
        )

        prospeo_name = self.normalize_name(
            prospeo_person.name
        )

        if web_name != prospeo_name:
            return False

        expected_company = self.normalize_company(
            company
        )

        actual_company = self.normalize_company(
            prospeo_person.company or ""
        )

        if not actual_company:
            return False

        return (
            expected_company in actual_company
            or actual_company in expected_company
        )