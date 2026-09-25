from agents.research_agent import ResearchAgent
from agents.scoring_agent import ScoringAgent
from agents.report_agent import ReportAgent
from agents.state import ResearchState


class ProspectIQ:

    def __init__(self):
        self.research_agent = ResearchAgent()
        self.scoring_agent = ScoringAgent()
        self.report_agent = ReportAgent()

    def analyze(
        self,
        company_name: str,
        research_goal: str,
    ):
        print("\n==============================")
        print("PROSPECTIQ ANALYSIS")
        print("==============================")

        # Step 1: Create initial research state
        state = ResearchState(
            company_name=company_name,
            research_goal=research_goal,
        )

        # Step 2: Research the company
        print("\n[1/3] RESEARCH")
        state = self.research_agent.run(state)

        # Step 3: Score the prospect
        print("\n[2/3] SCORING")
        score = self.scoring_agent.score(state)

        # Step 4: Generate final report
        print("\n[3/3] REPORT")
        report = self.report_agent.generate(
            state=state,
            score=score,
        )

        print("\n==============================")
        print("PROSPECTIQ ANALYSIS COMPLETE")
        print("==============================")

        return report