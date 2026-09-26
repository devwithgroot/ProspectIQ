from agents.state import ResearchState


def research_summary_block(state: ResearchState) -> str:
    avg_relevance = (
        f"{state.avg_relevance:.2f}"
        if state.avg_relevance is not None
        else "n/a"
    )
    avg_quality = (
        f"{state.avg_quality:.2f}"
        if state.avg_quality is not None
        else "n/a"
    )
    stop_reason = state.stop_reason or "n/a"

    return f"""
Research summary:
- Evidence count: {len(state.evidence)}
- Useful evidence count (relevance >= 0.35): {state.useful_evidence_count}
- Research stop reason: {stop_reason}
- Average relevance: {avg_relevance}
- Average quality: {avg_quality}
"""
