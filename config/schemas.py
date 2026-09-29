from pydantic import BaseModel, Field
from typing import Any, Literal


class Evidence(BaseModel):
    title: str
    url: str
    content: str
    source: str

    published_at: str | None = None

    relevance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    quality: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )

    evidence_type: str = "web"

class WebsiteContent(BaseModel):
    url: str
    title: str
    content: str
    status_code: int
    content_type: str

class ResearchDecision(BaseModel):
    action: str = Field(
        description="The next action. Must be either 'search' or 'finish'."
    )

    query: str | None = Field(
        default=None,
        description="Search query to execute when action is 'search'."
    )

    reasoning: str = Field(
        description="Brief explanation for why this action was selected."
    )


class Signal(BaseModel):
    type: str
    description: str
    strength: str = Field(
        description="Signal strength: low, medium, or high"
    )
    evidence: str

class ScoringAssessment(BaseModel):
    company_name: str

    growth_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    expansion_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    hiring_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    technology_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    strategic_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasons: list[str]


class ProspectAnalysis(BaseModel):
    company_name: str

    industry: str | None = None

    company_summary: str

    signals: list[Signal]

    pain_points: list[str]

    prospect_score: int = Field(
        ge=0,
        le=100,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    recommendation: str

class ProspectScore(BaseModel):
    company_name: str

    overall_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    growth_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    expansion_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    hiring_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    technology_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    strategic_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    recommendation: str

    reasons: list[str]

class ProspectReport(BaseModel):
    company_name: str

    executive_summary: str

    prospect_score: float = Field(
        ge=0.0,
        le=100.0,
    )

    recommendation: str

    key_signals: list[str]

    risks: list[str]

    recommended_sales_approach: str

    evidence: list[Evidence] = Field(
        default_factory=list
    )


class CompanySuggestion(BaseModel):
    name: str
    domain: str | None = None
    location: str | None = None
    description: str | None = None
    source_url: str | None = None


class PersonData(BaseModel):
    name: str

    title: str | None = None
    company: str | None = None
    location: str | None = None

    email: str | None = None
    mobile: str | None = None

    # ---------------------------------------------------------
    # PUBLIC WEB EVIDENCE
    # ---------------------------------------------------------

    source_url: str | None = None
    source_type: str | None = None
    evidence: str | None = None

    # ---------------------------------------------------------
    # PROSPEO
    # ---------------------------------------------------------

    prospeo_verified: bool = False
    prospeo_person_id: str | None = None

    # ---------------------------------------------------------
    # PROVENANCE
    # ---------------------------------------------------------

    data_sources: list[str] = Field(
        default_factory=list
    )

    confidence: float | None = None


class PeopleSearchResult(BaseModel):
    status: Literal[
        "success",
        "company_confirmation_required",
        "company_not_found",
        "no_people_found",
    ]

    searched_company: str

    resolved_company: str | None = None

    domain: str | None = None

    people: list[PersonData] = Field(
        default_factory=list
    )

    suggested_companies: list[
        CompanySuggestion
    ] = Field(
        default_factory=list
    )

    message: str | None = None



class News(BaseModel):
    company_name: str

    title: str
    url: str
    source: str | None = None
    published_at: str | None = None

    summary: str | None = None
    key_facts: list[str] = Field(default_factory=list)

    people_mentioned: list[str] = Field(default_factory=list)
    organizations_mentioned: list[str] = Field(default_factory=list)
    products_mentioned: list[str] = Field(default_factory=list)
    technologies_mentioned: list[str] = Field(default_factory=list)

    event_date: str | None = None
    location: str | None = None

    evidence: list[str] = Field(default_factory=list)