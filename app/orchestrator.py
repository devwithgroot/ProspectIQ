from collections.abc import Callable

from agents.research_agent import ResearchAgent
from agents.scoring_agent import ScoringAgent
from agents.report_agent import ReportAgent
from agents.state import ResearchState
from config.research_log import get_logger

log = get_logger("orchestrator")


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
        on_progress: Callable[[str], None] | None = None,
    ):
        log.info("Analyze start company=%s", company_name)
        state = ResearchState(
            company_name=company_name,
            research_goal=research_goal,
        )

        log.info("[1/3] Research %s", company_name)
        state = self.research_agent.run(state, on_progress=on_progress)

        log.info("[2/3] Scoring %s", company_name)
        score = self.scoring_agent.score(state, on_progress=on_progress)
        log.info(
            "Score %s overall=%.1f recommendation=%s",
            company_name,
            score.overall_score,
            score.recommendation,
        )

        log.info("[3/3] Report %s", company_name)
        report = self.report_agent.generate(
            state=state,
            score=score,
            on_progress=on_progress,
        )

        self.last_state = state
        log.info(
            "Analyze complete company=%s evidence=%s",
            company_name,
            len(state.evidence),
        )
        return report