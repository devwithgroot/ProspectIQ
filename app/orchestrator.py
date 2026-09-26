from collections.abc import Callable

from agents.research_agent import ResearchAgent
from agents.scoring_agent import ScoringAgent
from agents.report_agent import ReportAgent
from agents.state import ResearchState


class ProspectIQ:

    def __init__(self):
        self.research_agent = ResearchAgent()
        self.scoring_agent = ScoringAgent()
        self.report_agent = ReportAgent()
        self.last_state = None

    def analyze(
        self,
        company_name: str,
        research_goal: str,
        company_domain: str | None = None,
        on_progress: Callable[[str], None] | None = None,
    ):
        print("\n==============================")
        print("PROSPECTIQ ANALYSIS")
        print("==============================")

        # Step 1: Create initial research state
        state = ResearchState(
            company_name=company_name,
            research_goal=research_goal,
            company_domain=company_domain,
        )

        # Step 2: Research the company
        print("\n[1/3] RESEARCH")
        state = self.research_agent.run(state, on_progress=on_progress)

        # Step 3: Score the prospect
        print("\n[2/3] SCORING")
        score = self.scoring_agent.score(state, on_progress=on_progress)

        # Step 4: Generate final report
        print("\n[3/3] REPORT")
        report = self.report_agent.generate(
            state=state,
            score=score,
            on_progress=on_progress,
        )

        self.last_state = state

        print("\n==============================")
        print("PROSPECTIQ ANALYSIS COMPLETE")
        print("==============================")

        return report