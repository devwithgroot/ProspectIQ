from typing import Any
import re

from config.research_log import get_logger
from config.schemas import (
    PersonData,
    PeopleSearchResult,
)

from tools.base import BaseTool

from tools.providers.prospeo import (
    ProspeoProvider,
)

from tools.providers.tavily import (
    TavilyProvider,
)

log = get_logger("people")


class PeopleDataTool(BaseTool):
    """
    ProspectIQ people discovery + verification.

    Pipeline:

        Company
          ↓
        Tavily company resolution
          ↓
        Tavily multi-source people discovery
          ↓
        Deduplicated web people
          ↓
        ONE Prospeo company search
          ↓
        Local identity matching
          ↓
        Web identity remains authoritative
          ↓
        Prospeo only enriches matched people
    """

    name = "people_data"

    description = (
        "Discover relevant people and decision makers "
        "within a company using public web research, "
        "LinkedIn discovery and structured Prospeo "
        "verification."
    )

    def __init__(
        self,
        provider: ProspeoProvider | None = None,
        web_provider: TavilyProvider | None = None,
    ) -> None:

        self.provider = (
            provider
            if provider is not None
            else ProspeoProvider()
        )

        self.web_provider = (
            web_provider
            if web_provider is not None
            else TavilyProvider()
        )

    # =========================================================
    # EXECUTE
    # =========================================================

    def execute(
        self,
        company: str | None = None,
        title: str | None = None,
        location: str | None = None,
        limit: int = 10,
        **kwargs: Any,
    ) -> PeopleSearchResult:

        if not company:

            raise ValueError(
                "Company name is required."
            )

        searched_company = (
            company.strip()
        )

        print(
            "\n[1/4] Resolving company..."
        )

        # =====================================================
        # STEP 1 — COMPANY RESOLUTION
        # =====================================================

        resolution = (
            self.web_provider.resolve_company(
                searched_company
            )
        )

        if not resolution.get(
            "resolved"
        ):

            print(
                "[INFO] Company could not "
                "be confidently resolved."
            )

            suggestions = (
                self.web_provider.suggest_companies(
                    searched_company,
                    limit=5,
                )
            )

            return PeopleSearchResult(
                status=(
                    "company_confirmation_required"
                    if suggestions
                    else "company_not_found"
                ),
                searched_company=searched_company,
                suggested_companies=suggestions,
                message=(
                    f"I could not confidently "
                    f"identify '{searched_company}'. "
                    "Please select the correct "
                    "company or provide its full "
                    "legal name or website."
                ),
            )

        resolved_company = (
            resolution.get("company")
            or searched_company
        )

        domain = resolution.get(
            "domain"
        )

        print(
            f"[INFO] Company: "
            f"{resolved_company}"
        )

        if domain:

            print(
                f"[INFO] Domain: {domain}"
            )

        # =====================================================
        # STEP 2 — WEB PEOPLE DISCOVERY
        # =====================================================

        print(
            "\n[2/4] Searching public web "
            "and LinkedIn for people..."
        )

        web_people = (
            self.web_provider.search_company_people(
                company=resolved_company,
                title=title,
                location=location,
                limit=limit,
            )
        )

        print(
            f"[INFO] Unique web people found: "
            f"{len(web_people)}"
        )

        if not web_people:

            return PeopleSearchResult(
                status="no_people_found",
                searched_company=searched_company,
                resolved_company=resolved_company,
                domain=domain,
                message=(
                    "The company was identified, "
                    "but no relevant people could "
                    "be confidently found from "
                    "public sources."
                ),
            )

        # =====================================================
        # STEP 3 — ONE PROSPEO COMPANY SEARCH
        # =====================================================

        print(
            "\n[3/4] Searching Prospeo for "
            "company people..."
        )

        try:

            prospeo_people = (
                self.provider.search_people(
                    company=resolved_company,
                    limit=max(
                        25,
                        limit * 3,
                    ),
                )
            )

        except Exception as exc:

            print(
                "[WARN] Prospeo search failed:"
            )

            print(
                f"[WARN] {exc}"
            )

            prospeo_people = []

        print(
            f"[INFO] Prospeo people found: "
            f"{len(prospeo_people)}"
        )

        # =====================================================
        # STEP 4 — LOCAL MATCHING
        # =====================================================

        print(
            "\n[4/4] Matching web people "
            "against Prospeo..."
        )

        final_people: list[
            PersonData
        ] = []

        for web_person in web_people:

            matched_person = None

            for prospeo_person in prospeo_people:

                if self._person_matches(
                    web_person=web_person,
                    prospeo_person=prospeo_person,
                    company=resolved_company,
                ):

                    matched_person = (
                        prospeo_person
                    )

                    break

            if matched_person:

                print(
                    f"[MATCH] "
                    f"{web_person.name}"
                )

                final_people.append(
                    self._merge_prospeo(
                        web_person,
                        matched_person,
                    )
                )

            else:

                print(
                    f"[WEB ONLY] "
                    f"{web_person.name}"
                )

                # Web identity remains valid.
                web_person.prospeo_verified = False

                if "web" not in web_person.data_sources:

                    web_person.data_sources.append(
                        "web"
                    )

                final_people.append(
                    web_person
                )

        # =====================================================
        # RESULT
        # =====================================================

        return PeopleSearchResult(
            status="success",
            searched_company=searched_company,
            resolved_company=resolved_company,
            domain=domain,
            people=final_people,
            message=(
                f"Found {len(final_people)} "
                "unique people from public "
                "web research. Prospeo was "
                "used for identity matching "
                "and structured enrichment."
            ),
        )

    # =========================================================
    # PERSON MATCHING
    # =========================================================

    @staticmethod
    def _person_matches(
        web_person: PersonData,
        prospeo_person: PersonData,
        company: str,
    ) -> bool:

        web_name = (
            PeopleDataTool._normalize_name(
                web_person.name
            )
        )

        prospeo_name = (
            PeopleDataTool._normalize_name(
                prospeo_person.name
            )
        )

        # -----------------------------------------------------
        # NAME MUST MATCH
        # -----------------------------------------------------

        if web_name != prospeo_name:

            return False

        # -----------------------------------------------------
        # COMPANY MUST MATCH
        # -----------------------------------------------------

        expected_company = (
            PeopleDataTool._normalize_company(
                company
            )
        )

        actual_company = (
            PeopleDataTool._normalize_company(
                prospeo_person.company
                or ""
            )
        )

        if not actual_company:

            return False

        if (
            expected_company in actual_company
            or actual_company in expected_company
        ):

            return True

        return False

    # =========================================================
    # NAME NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_name(
        value: str,
    ) -> str:

        value = value.lower().strip()

        value = re.sub(
            r"^(mr|mrs|ms|miss|dr)\.?\s+",
            "",
            value,
            flags=re.IGNORECASE,
        )

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

        return value.strip()

    # =========================================================
    # COMPANY NORMALIZATION
    # =========================================================

    @staticmethod
    def _normalize_company(
        value: str,
    ) -> str:

        value = value.lower()

        value = re.sub(
            r"\b(private|pvt|limited|ltd|llp|"
            r"inc|incorporated|corporation|corp)\b",
            "",
            value,
        )

        value = re.sub(
            r"[^a-z0-9]",
            "",
            value,
        )

        return value

    # =========================================================
    # MERGE
    # =========================================================

    @staticmethod
    def _merge_prospeo(
        web_person: PersonData,
        prospeo_person: PersonData,
    ) -> PersonData:

        # -----------------------------------------------------
        # IMPORTANT:
        #
        # WEB IDENTITY WINS.
        #
        # Never overwrite:
        #   name
        #   title
        #   company
        #
        # with Prospeo values.
        # -----------------------------------------------------

        web_person.prospeo_verified = True

        web_person.prospeo_person_id = (
            prospeo_person.prospeo_person_id
        )

        # -----------------------------------------------------
        # Prospeo contact information
        # -----------------------------------------------------

        if prospeo_person.email:

            web_person.email = (
                prospeo_person.email
            )

        if prospeo_person.mobile:

            web_person.mobile = (
                prospeo_person.mobile
            )

        # -----------------------------------------------------
        # Provenance
        # -----------------------------------------------------

        if (
            "prospeo"
            not in web_person.data_sources
        ):

            web_person.data_sources.append(
                "prospeo"
            )

        web_person.confidence = 0.95

        return web_person