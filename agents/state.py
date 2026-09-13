from pydantic import BaseModel, Field

from config.schemas import Evidence


class ResearchState(BaseModel):
    company_name: str

    research_goal: str

    evidence: list[Evidence] = Field(
        default_factory=list
    )

    queries: list[str] = Field(
        default_factory=list
    )

    steps_taken: int = 0

    max_steps: int = 5