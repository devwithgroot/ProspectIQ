import os
import re
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient

from config.schemas import (
    CompanySuggestion,
    PersonData,
)

load_dotenv()


class TavilyProvider:
    """
    Public web research provider for ProspectIQ.

    Responsibilities:

    1. Resolve company identity.
    2. Discover relevant people.
    3. Search official websites.
    4. Search LinkedIn company pages.
    5. Search LinkedIn people profiles.
    6. Preserve source URLs and evidence.
    7. Deduplicate people discovered from multiple sources.

    Tavily is used for discovery and evidence.

    Prospeo is used later for structured verification/enrichment.
    """

    def __init__(
        self,
        api_key: str | None = None,
    ) -> None:

        self.api_key = (
            api_key
            or os.getenv("TAVILY_API_KEY")
        )

        if not self.api_key:
            raise ValueError(
                "TAVILY_API_KEY is not set."
            )

        self.client = TavilyClient(
            api_key=self.api_key
        )

    # =========================================================
    # GENERIC SEARCH
    # =========================================================

    def _search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:

        try:

            response = self.client.search(
                query=query,
                search_depth="advanced",
                max_results=max_results,
                include_answer=True,
            )

            return response.get(
                "results",
                []
            )

        except Exception as exc:

            print(
                f"[WARN] Tavily search failed: "
                f"{query}"
            )

            print(
                f"[WARN] {exc}"
            )

            return []

    # =========================================================
    # COMPANY RESOLUTION
    # =========================================================

    def resolve_company(
        self,
        company: str,
    ) -> dict[str, Any]:

        queries = [
            f'"{company}" official company',
            f'"{company}" official website',
            f'"{company}" company profile',
            f'"{company}" headquarters',
        ]

        all_results: list[dict[str, Any]] = []

        for query in queries:

            results = self._search(
                query,
                max_results=5,
            )

            all_results.extend(results)

        if not all_results:

            return {
                "resolved": False,
                "company": None,
                "domain": None,
                "source_url": None,
                "evidence": None,
            }

        # -----------------------------------------------------
        # Find the strongest company-looking result.
        # -----------------------------------------------------

        best_result = None

        for result in all_results:

            url = (
                result.get("url")
                or ""
            ).lower()

            title = (
                result.get("title")
                or ""
            ).lower()

            content = (
                result.get("content")
                or ""
            ).lower()

            # Prefer official-looking results.
            if any(
                x in url
                for x in [
                    "linkedin.com/company",
                    "company",
                    "official",
                ]
            ):
                best_result = result
                break

            if company.lower() in title:
                best_result = result
                break

            if company.lower() in content:
                best_result = result

        if best_result is None:
            best_result = all_results[0]

        source_url = best_result.get(
            "url"
        )

        evidence = best_result.get(
            "content"
        )

        # -----------------------------------------------------
        # We deliberately keep the user's company name unless
        # we have strong evidence for another legal name.
        #
        # This avoids incorrectly turning:
        #
        # Everest Ply
        #
        # into an unrelated company just because Tavily
        # returned IndiaMART or another directory.
        # -----------------------------------------------------

        resolved_company = company

        # Try to detect a more complete company name.
        extracted = self._extract_company_name(
            evidence or ""
        )

        if extracted:
            resolved_company = extracted

        domain = self._domain_from_url(
            source_url
        )

        return {
            "resolved": True,
            "company": resolved_company,
            "domain": domain,
            "source_url": source_url,
            "evidence": evidence,
        }

    # =========================================================
    # COMPANY SUGGESTIONS
    # =========================================================

    def suggest_companies(
        self,
        company: str,
        limit: int = 5,
    ) -> list[CompanySuggestion]:

        query = (
            f'companies similar to "{company}" '
            f'company official website'
        )

        results = self._search(
            query,
            max_results=10,
        )

        suggestions: list[
            CompanySuggestion
        ] = []

        seen: set[str] = set()

        for result in results:

            title = (
                result.get("title")
                or ""
            ).strip()

            content = (
                result.get("content")
                or ""
            ).strip()

            url = result.get(
                "url"
            )

            if not title:
                continue

            candidate = self._clean_company_title(
                title
            )

            if not candidate:
                continue

            key = candidate.lower()

            if key in seen:
                continue

            seen.add(key)

            suggestions.append(
                CompanySuggestion(
                    name=candidate,
                    domain=self._domain_from_url(
                        url
                    ),
                    description=content[:300]
                    if content
                    else None,
                    source_url=url,
                )
            )

            if len(suggestions) >= limit:
                break

        return suggestions

    # =========================================================
    # PEOPLE DISCOVERY
    # =========================================================

    def search_company_people(
        self,
        company: str,
        title: str | None = None,
        location: str | None = None,
        limit: int = 10,
    ) -> list[PersonData]:

        """
        Search broadly for people associated with a company.

        We intentionally perform multiple searches because a
        single Google/Tavily query can repeatedly return the
        same person.
        """

        queries: list[str] = []

        # -----------------------------------------------------
        # Leadership
        # -----------------------------------------------------

        queries.extend(
            [
                f'"{company}" leadership',
                f'"{company}" management team',
                f'"{company}" directors',
                f'"{company}" executives',
                f'"{company}" CEO',
                f'"{company}" founder',
                f'"{company}" owner',
                f'"{company}" managing director',
                f'"{company}" executive director',
                f'"{company}" CFO',
                f'"{company}" CTO',
                f'"{company}" COO',
            ]
        )

        # -----------------------------------------------------
        # Official website
        # -----------------------------------------------------

        queries.extend(
            [
                f'"{company}" official website leadership',
                f'"{company}" official website management',
                f'"{company}" official website directors',
                f'"{company}" official website team',
            ]
        )

        # -----------------------------------------------------
        # LinkedIn company
        # -----------------------------------------------------

        queries.extend(
            [
                f'site:linkedin.com/company "{company}"',
                f'site:linkedin.com/company "{company}" leadership',
                f'site:linkedin.com/company "{company}" employees',
            ]
        )

        # -----------------------------------------------------
        # LinkedIn individual profiles
        # -----------------------------------------------------

        queries.extend(
            [
                f'site:linkedin.com/in "{company}" CEO',
                f'site:linkedin.com/in "{company}" founder',
                f'site:linkedin.com/in "{company}" owner',
                f'site:linkedin.com/in "{company}" director',
                f'site:linkedin.com/in "{company}" "Managing Director"',
                f'site:linkedin.com/in "{company}" executive',
                f'site:linkedin.com/in "{company}" CFO',
                f'site:linkedin.com/in "{company}" CTO',
            ]
        )

        # -----------------------------------------------------
        # Location
        # -----------------------------------------------------

        if location:

            queries.extend(
                [
                    f'"{company}" "{location}" director',
                    f'"{company}" "{location}" CEO',
                    f'site:linkedin.com/in "{company}" "{location}"',
                ]
            )

        # -----------------------------------------------------
        # Specific title
        # -----------------------------------------------------

        if title:

            queries.insert(
                0,
                f'"{company}" "{title}"',
            )

            queries.insert(
                1,
                f'site:linkedin.com/in "{company}" "{title}"',
            )

        # -----------------------------------------------------
        # Collect + deduplicate
        # -----------------------------------------------------

        people_by_key: dict[
            str,
            PersonData,
        ] = {}

        for query in queries:

            results = self._search(
                query,
                max_results=5,
            )

            for result in results:

                candidates = (
                    self._extract_people_from_result(
                        company=company,
                        result=result,
                    )
                )

                for person in candidates:

                    key = self._person_key(
                        person.name
                    )

                    if not key:
                        continue

                    if key not in people_by_key:

                        people_by_key[key] = person

                    else:

                        self._merge_web_evidence(
                            people_by_key[key],
                            person,
                        )

        people = list(
            people_by_key.values()
        )

        # -----------------------------------------------------
        # Sort by source quality.
        # -----------------------------------------------------

        people.sort(
            key=self._source_priority,
            reverse=True,
        )

        return people[:limit]

    # =========================================================
    # PEOPLE EXTRACTION
    # =========================================================

    def _extract_people_from_result(
        self,
        company: str,
        result: dict[str, Any],
    ) -> list[PersonData]:

        title = (
            result.get("title")
            or ""
        )

        content = (
            result.get("content")
            or ""
        )

        url = result.get(
            "url"
        )

        text = (
            f"{title}\n{content}"
        )

        people: list[
            PersonData
        ] = []

        role_pattern = (
            r"CEO|Chief Executive Officer|"
            r"Founder|Co-Founder|"
            r"Owner|"
            r"Director|"
            r"Managing Director|"
            r"Joint Managing Director|"
            r"Executive Director|"
            r"CFO|Chief Financial Officer|"
            r"CTO|Chief Technology Officer|"
            r"COO|Chief Operating Officer|"
            r"President|"
            r"Vice President|"
            r"General Manager"
        )

        patterns = [

            # Name - Role
            rf"\b"
            rf"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)?\s*"
            rf"([A-Z][A-Za-z.\-']+"
            rf"(?:\s+[A-Z][A-Za-z.\-']+){{1,4}})"
            rf"\s*[-,:]\s*"
            rf"({role_pattern})"
            rf"\b",

            # Role - Name
            rf"\b"
            rf"({role_pattern})"
            rf"\s*[-,:]\s*"
            rf"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)?\s*"
            rf"([A-Z][A-Za-z.\-']+"
            rf"(?:\s+[A-Z][A-Za-z.\-']+){{1,4}})"
            rf"\b",

            # Name, Role
            rf"\b"
            rf"(?:Mr\.?|Mrs\.?|Ms\.?|Dr\.?)?\s*"
            rf"([A-Z][A-Za-z.\-']+"
            rf"(?:\s+[A-Z][A-Za-z.\-']+){{1,4}})"
            rf"\s*,\s*"
            rf"({role_pattern})"
            rf"\b",
        ]

        for pattern in patterns:

            try:

                matches = re.findall(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )

            except re.error:
                continue

            for match in matches:

                if len(match) != 2:
                    continue

                first = match[0].strip()
                second = match[1].strip()

                if self._looks_like_role(first):

                    person_name = second
                    person_title = first

                else:

                    person_name = first
                    person_title = second

                person_name = (
                    self._clean_person_name(
                        person_name
                    )
                )

                if not self._valid_person_name(
                    person_name
                ):
                    continue

                if self._contains_bad_name_tokens(
                    person_name
                ):
                    continue

                people.append(
                    PersonData(
                        name=person_name,
                        title=person_title,
                        company=company,
                        location=None,
                        source_url=url,
                        source_type=self._source_type(
                            url
                        ),
                        evidence=self._clean_evidence(
                            content
                        ),
                        prospeo_verified=False,
                        data_sources=["web"],
                        confidence=0.65,
                    )
                )

        return people

    # =========================================================
    # PERSON NORMALIZATION
    # =========================================================

    @staticmethod
    def _person_key(
        name: str,
    ) -> str:

        name = name.lower().strip()

        name = re.sub(
            r"^(mr|mrs|ms|miss|dr)\.?\s+",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"\bdesignation\b",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"[^a-z0-9\s]",
            " ",
            name,
        )

        name = re.sub(
            r"\s+",
            " ",
            name,
        )

        return name.strip()

    @staticmethod
    def _clean_person_name(
        name: str,
    ) -> str:

        name = name.strip()

        name = re.sub(
            r"^(Mr|Mrs|Ms|Miss|Dr)\.?\s+",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"\s+(Designation|Title|Position)$",
            "",
            name,
            flags=re.IGNORECASE,
        )

        name = re.sub(
            r"\s+",
            " ",
            name,
        )

        return name.strip()

    @staticmethod
    def _valid_person_name(
        name: str,
    ) -> bool:

        words = name.split()

        if len(words) < 2:
            return False

        if len(name) > 100:
            return False

        # Reject obvious non-person strings.
        bad = {
            "customer",
            "website",
            "designation",
            "directorate",
            "management",
            "leadership",
            "company",
            "industries",
            "enterprise",
        }

        if any(
            word.lower() in bad
            for word in words
        ):
            return False

        return all(
            re.match(
                r"^[A-Za-z.\-']+$",
                word,
            )
            for word in words
        )

    @staticmethod
    def _contains_bad_name_tokens(
        name: str,
    ) -> bool:

        bad_tokens = {
            "designation",
            "title",
            "position",
            "website",
            "customer",
            "contact",
            "email",
            "phone",
        }

        tokens = {
            token.lower()
            for token in name.split()
        }

        return bool(
            tokens.intersection(
                bad_tokens
            )
        )

    # =========================================================
    # EVIDENCE MERGING
    # =========================================================

    @staticmethod
    def _merge_web_evidence(
        existing: PersonData,
        new: PersonData,
    ) -> None:

        # -----------------------------------------------------
        # Keep the best title.
        # -----------------------------------------------------

        if (
            not existing.title
            and new.title
        ):
            existing.title = new.title

        # -----------------------------------------------------
        # Add evidence from another source.
        # -----------------------------------------------------

        if new.source_url:

            existing_urls = (
                existing.evidence
                or ""
            )

            marker = (
                f"Source: {new.source_url}"
            )

            if marker not in existing_urls:

                existing.evidence = (
                    existing_urls
                    + "\n\n"
                    + marker
                    + "\n"
                    + (
                        new.evidence
                        or ""
                    )
                )

        # -----------------------------------------------------
        # Multiple independent sources increase confidence.
        # -----------------------------------------------------

        existing.confidence = min(
            0.90,
            (existing.confidence or 0.65)
            + 0.05,
        )

    # =========================================================
    # SOURCE QUALITY
    # =========================================================

    @staticmethod
    def _source_priority(
        person: PersonData,
    ) -> int:

        source = (
            person.source_type
            or ""
        ).lower()

        if source == "official_company":
            return 100

        if source == "linkedin_company":
            return 90

        if source == "linkedin_profile":
            return 85

        if source == "company_filing":
            return 90

        if source == "public_web":
            return 70

        if source == "social_media":
            return 40

        return 50

    # =========================================================
    # SOURCE TYPE
    # =========================================================

    @staticmethod
    def _source_type(
        url: str | None,
    ) -> str:

        if not url:
            return "public_web"

        url_lower = url.lower()

        if "linkedin.com/company" in url_lower:
            return "linkedin_company"

        if "linkedin.com/in" in url_lower:
            return "linkedin_profile"

        if "instagram.com" in url_lower:
            return "social_media"

        if "facebook.com" in url_lower:
            return "social_media"

        return "public_web"

    # =========================================================
    # EVIDENCE
    # =========================================================

    @staticmethod
    def _clean_evidence(
        content: str,
    ) -> str:

        content = re.sub(
            r"\s+",
            " ",
            content,
        )

        return content[:1200]

    # =========================================================
    # ROLE
    # =========================================================

    @staticmethod
    def _looks_like_role(
        value: str,
    ) -> bool:

        roles = {
            "ceo",
            "chief executive officer",
            "founder",
            "co-founder",
            "owner",
            "director",
            "managing director",
            "joint managing director",
            "executive director",
            "cfo",
            "chief financial officer",
            "cto",
            "chief technology officer",
            "coo",
            "chief operating officer",
            "president",
            "vice president",
            "general manager",
        }

        return (
            value.lower().strip()
            in roles
        )

    # =========================================================
    # COMPANY HELPERS
    # =========================================================

    @staticmethod
    def _extract_company_name(
        content: str,
    ) -> str | None:

        if not content:
            return None

        patterns = [
            r"([A-Z][A-Za-z&.\- ]{2,80}"
            r"(?:Private Limited|Pvt Ltd|Limited|Ltd|LLP))",

            r"([A-Z][A-Za-z&.\- ]{2,80}"
            r"(?:Industries|Enterprises|Corporation|"
            r"Corporations|Group|Holdings))",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                content,
            )

            if match:

                value = (
                    match.group(1)
                    .strip()
                )

                if len(value) < 150:
                    return value

        return None

    @staticmethod
    def _clean_company_title(
        title: str,
    ) -> str:

        title = re.sub(
            r"\s*[-|].*$",
            "",
            title,
        )

        title = title.strip()

        return title[:150]

    @staticmethod
    def _domain_from_url(
        url: str | None,
    ) -> str | None:

        if not url:
            return None

        match = re.search(
            r"https?://([^/]+)",
            url,
        )

        if not match:
            return None

        return match.group(1).lower()