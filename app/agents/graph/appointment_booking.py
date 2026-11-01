"""LangGraph Appointment Booking Agent with HITL Workflow (Phase 5)."""

from typing import Any, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

# Out-of-scope & Unsupported keyword filters
from app.agents.nodes.appointment_booking import (
    booking_agent_node,
    booking_tool_execution_node,
    classify_booking_intent_node,
    post_approval_atomic_booking_node,
    prepare_proposal_node,
)
from app.agents.state import AppointmentBookingState


def booking_should_continue_router(
    state: AppointmentBookingState,
) -> Literal["tools", "end"]:
    """Conditional Edge Router: Route pre-approval agent to tools or END."""
    intent = state.get("intent")
    if intent in ("OUT_OF_SCOPE", "UNSUPPORTED"):
        return "end"

    if state.get("error") or state.get("booking_proposal"):
        return "end"

    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_msg = messages[-1]
    if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
        return "tools"

    return "end"


def build_appointment_booking_graph(llm: Optional[BaseChatModel] = None) -> Any:
    """Build and compile the LangGraph Appointment Booking workflow graph."""
    workflow = StateGraph(AppointmentBookingState)

    workflow.add_node("classify_intent", classify_booking_intent_node)
    workflow.add_node("prepare_proposal", prepare_proposal_node)

    def agent_node(state: AppointmentBookingState):
        return booking_agent_node(state, llm=llm)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", booking_tool_execution_node)
    workflow.add_node("atomic_book", post_approval_atomic_booking_node)

    workflow.add_edge(START, "classify_intent")

    def route_intent(
        state: AppointmentBookingState,
    ) -> Literal["prepare_proposal", "end"]:
        if state.get("intent") in ("OUT_OF_SCOPE", "UNSUPPORTED"):
            return "end"
        return "prepare_proposal"

    workflow.add_conditional_edges(
        "classify_intent",
        route_intent,
        {"prepare_proposal": "prepare_proposal", "end": END},
    )

    def route_proposal(
        state: AppointmentBookingState,
    ) -> Literal["atomic_book", "agent", "end"]:
        if state.get("approval_status") == "APPROVED":
            return "atomic_book"
        if state.get("booking_proposal"):
            return "end"
        return "agent"

    workflow.add_conditional_edges(
        "prepare_proposal",
        route_proposal,
        {"atomic_book": "atomic_book", "agent": "agent", "end": END},
    )

    workflow.add_conditional_edges(
        "agent", booking_should_continue_router, {"tools": "tools", "end": END}
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("atomic_book", END)

    return workflow.compile()
