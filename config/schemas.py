from pydantic import BaseModel, Field


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