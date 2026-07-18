"""LangGraph Multi-Agent Orchestrator State and Supervisor.

Defines the shared AgentState TypedDict and the Supervisor StateGraph
that orchestrates all 12 specialized legal analysis agents.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from loguru import logger


# ── Agent State Schema ──────────────────────────────────────
class AgentState(TypedDict, total=False):
    """Shared state passed between all agents in the LangGraph workflow.

    Each agent reads relevant fields and writes its outputs back.
    The Supervisor routes based on completion status.
    """

    # Input
    case_id: str
    query: str
    documents: list[dict[str, Any]]

    # Case Understanding outputs
    case_summary: str
    case_facts: dict[str, Any]
    entities: dict[str, Any]
    timeline: list[dict[str, Any]]

    # Legal Research outputs
    legal_issues: list[str]
    applicable_acts: list[str]
    applicable_sections: list[dict[str, Any]]
    precedents: list[dict[str, Any]]

    # Knowledge Graph outputs
    kg_data: dict[str, Any]

    # Evidence Reliability outputs
    evidence_assessment: dict[str, Any]

    # Contradiction Detection outputs
    contradictions: list[dict[str, Any]]

    # Procedural Compliance outputs
    procedural_status: dict[str, Any]

    # Legal Reasoning outputs
    legal_reasoning: str
    irac_analysis: dict[str, Any]

    # Strategy Recommendation outputs
    strategy_options: list[dict[str, Any]]

    # Risk Assessment outputs
    risk_assessment: dict[str, Any]

    # Confidence Fusion outputs
    agent_confidence: dict[str, float]
    trust_score: float

    # Explainability outputs
    explanation_graph: dict[str, Any]

    # Report Generation outputs
    final_report: dict[str, Any]

    # Control flow
    messages: Annotated[list[Any], add_messages]
    completed_agents: list[str]
    errors: list[str]
    next_agent: str


# ── Agent Routing Logic ─────────────────────────────────────
AGENT_SEQUENCE = [
    "case_understanding",
    "legal_research",
    "knowledge_graph",
    "evidence_reliability",
    "contradiction_detection",
    "procedural_compliance",
    "legal_reasoning",
    "strategy_recommendation",
    "risk_assessment",
    "confidence_fusion",
    "explainability",
    "report_generation",
]


def supervisor_router(state: AgentState) -> Literal[
    "case_understanding",
    "legal_research",
    "knowledge_graph",
    "evidence_reliability",
    "contradiction_detection",
    "procedural_compliance",
    "legal_reasoning",
    "strategy_recommendation",
    "risk_assessment",
    "confidence_fusion",
    "explainability",
    "report_generation",
    "__end__",
]:
    """Route to the next agent based on completion status.

    Each agent adds its name to state["completed_agents"] when done.
    The supervisor routes to the first incomplete agent in the sequence.
    """
    completed = state.get("completed_agents", [])

    for agent in AGENT_SEQUENCE:
        if agent not in completed:
            return agent  # type: ignore[return-value]

    return "__end__"


# ── Supervisor Graph Construction ──────────────────────────
def build_supervisor_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph with all 12 agents.

    The supervisor graph:
    1. Starts at case_understanding
    2. After each agent completes, routes to the next agent
    3. Ends at report_generation
    4. On error in any agent, records error and continues
    """
    from app.agents.analysis import case_understanding_agent
    from app.agents.analysis import legal_research_agent
    from app.agents.analysis import knowledge_graph_agent
    from app.agents.analysis import evidence_reliability_agent
    from app.agents.analysis import contradiction_detection_agent
    from app.agents.analysis import procedural_compliance_agent
    from app.agents.analysis import legal_reasoning_agent
    from app.agents.analysis import strategy_recommendation_agent
    from app.agents.analysis import risk_assessment_agent
    from app.agents.analysis import confidence_fusion_agent
    from app.agents.analysis import explainability_agent
    from app.agents.analysis import report_generation_agent

    # Create the graph
    workflow = StateGraph(AgentState)

    # Add all agent nodes
    workflow.add_node("case_understanding", case_understanding_agent)
    workflow.add_node("legal_research", legal_research_agent)
    workflow.add_node("knowledge_graph", knowledge_graph_agent)
    workflow.add_node("evidence_reliability", evidence_reliability_agent)
    workflow.add_node("contradiction_detection", contradiction_detection_agent)
    workflow.add_node("procedural_compliance", procedural_compliance_agent)
    workflow.add_node("legal_reasoning", legal_reasoning_agent)
    workflow.add_node("strategy_recommendation", strategy_recommendation_agent)
    workflow.add_node("risk_assessment", risk_assessment_agent)
    workflow.add_node("confidence_fusion", confidence_fusion_agent)
    workflow.add_node("explainability", explainability_agent)
    workflow.add_node("report_generation", report_generation_agent)

    # Set entry point
    workflow.set_entry_point("case_understanding")

    # Add conditional edges from each agent back to the supervisor router
    for agent_name in AGENT_SEQUENCE:
        workflow.add_conditional_edges(
            agent_name,
            supervisor_router,
            {name: name for name in AGENT_SEQUENCE + ["__end__"]},
        )

    return workflow.compile()


# ── Supervisor Execution ────────────────────────────────────
async def run_analysis_pipeline(
    case_id: str,
    query: str = "",
    documents: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute the full multi-agent analysis pipeline for a legal case.

    Args:
        case_id: The database case ID.
        query: Optional specific legal question about the case.
        documents: List of parsed document dicts.

    Returns:
        Final state containing all agent outputs.
    """
    logger.info(f"Starting analysis pipeline for case: {case_id}")

    initial_state: AgentState = {
        "case_id": case_id,
        "query": query,
        "documents": documents or [],
        "completed_agents": [],
        "errors": [],
        "agent_confidence": {},
    }

    try:
        graph = build_supervisor_graph()
        final_state = await graph.ainvoke(initial_state)
        logger.info(f"Analysis pipeline complete for case: {case_id}")
        return final_state
    except Exception as exc:
        logger.error(f"Analysis pipeline failed for case {case_id}: {exc}")
        return {
            **initial_state,
            "errors": [str(exc)],
            "final_report": {"error": str(exc)},
        }
