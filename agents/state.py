from typing import Literal

from pydantic import BaseModel, Field

from config.schemas import Evidence

ResearchStopReason = Literal[
    "finish",
    "max_steps",
    "duplicate_query_exhausted",
    "invalid_planner_exhausted",
    "search_failed_exhausted",
]


class ResearchState(BaseModel):
    company_name: str

    research_goal: str

    company_domain: str | None = None

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    queries: list[str] = Field(
        default_factory=list
    )

    steps_taken: int = 0

    max_steps: int = 5

    stop_reason: ResearchStopReason | None = None

    avg_relevance: float | None = None

    avg_quality: float | None = None

    useful_evidence_count: int = 0
