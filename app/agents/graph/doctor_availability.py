"""LangGraph Doctor Availability Agent Graph Workflow (Phase 4)."""

from typing import Any, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

# Out-of-scope & Unsupported keyword filters
from app.agents.nodes.doctor_availability import (
    availability_agent_node,
    availability_tool_execution_node,
    classify_availability_intent_node,
)
from app.agents.state import DoctorAvailabilityState


def availability_should_continue_router(
    state: DoctorAvailabilityState,
) -> Literal["tools", "end"]:
    """Conditional Edge Router: Route to tools or end workflow."""
    intent = state.get("intent")
    if intent in ("OUT_OF_SCOPE", "UNSUPPORTED", "BOOKING_REQUEST"):
        return "end"

    if state.get("error"):
        return "end"

    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"

    return "end"


def build_doctor_availability_graph(llm: Optional[BaseChatModel] = None) -> Any:
    """Build and compile the LangGraph Doctor Availability workflow graph."""
    workflow = StateGraph(DoctorAvailabilityState)

    workflow.add_node("classify_intent", classify_availability_intent_node)

    def agent_node(state: DoctorAvailabilityState):
        return availability_agent_node(state, llm=llm)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", availability_tool_execution_node)

    workflow.add_edge(START, "classify_intent")

    def route_intent(state: DoctorAvailabilityState) -> Literal["agent", "end"]:
        if state.get("intent") in ("OUT_OF_SCOPE", "UNSUPPORTED", "BOOKING_REQUEST"):
            return "end"
        return "agent"

    workflow.add_conditional_edges(
        "classify_intent", route_intent, {"agent": "agent", "end": END}
    )
    workflow.add_conditional_edges(
        "agent", availability_should_continue_router, {"tools": "tools", "end": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
