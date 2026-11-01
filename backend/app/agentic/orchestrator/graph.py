"""Orchestration graph; it routes only and delegates all business operations."""

from langgraph.graph import END, START, StateGraph

from app.agentic.orchestrator.nodes import clarify, dispatch, route_request
from app.agentic.orchestrator.state import OrchestratorState


def build_orchestrator_graph():
    graph = StateGraph(OrchestratorState)
    graph.add_node("route", route_request)
    graph.add_node("clarify", clarify)
    graph.add_node("dispatch", dispatch)
    graph.add_edge(START, "route")
    graph.add_conditional_edges(
        "route",
        lambda state: "clarify" if state["intent"] == "clarify" else "dispatch",
        {"clarify": "clarify", "dispatch": "dispatch"},
    )
    graph.add_edge("clarify", END)
    graph.add_edge("dispatch", END)
    return graph.compile()
