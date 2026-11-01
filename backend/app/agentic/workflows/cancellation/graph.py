"""LangGraph Appointment Cancellation Agent with HITL Workflow (Phase 6)."""

from typing import Any, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.agentic.workflows.cancellation.nodes import (
    cancellation_agent_node,
    cancellation_tool_execution_node,
    classify_cancellation_intent_node,
    identify_and_authorize_appointment_node,
    post_approval_atomic_cancellation_node,
    prepare_cancellation_proposal_node,
)
from app.agentic.workflows.cancellation.state import AppointmentCancellationState


def build_appointment_cancellation_graph(llm: Optional[BaseChatModel] = None) -> Any:
    """Build and compile the LangGraph Appointment Cancellation workflow graph."""
    workflow = StateGraph(AppointmentCancellationState)

    workflow.add_node("classify_intent", classify_cancellation_intent_node)
    workflow.add_node("identify_appointment", identify_and_authorize_appointment_node)
    workflow.add_node("prepare_proposal", prepare_cancellation_proposal_node)

    def agent_node(state: AppointmentCancellationState):
        return cancellation_agent_node(state, llm=llm)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", cancellation_tool_execution_node)
    workflow.add_node("atomic_cancel", post_approval_atomic_cancellation_node)

    workflow.add_edge(START, "classify_intent")

    def route_intent(
        state: AppointmentCancellationState,
    ) -> Literal["identify_appointment", "prepare_proposal", "end"]:
        if state.get("intent") == "OUT_OF_SCOPE":
            return "end"
        if state.get("approval_status") == "APPROVED" or state.get(
            "cancellation_proposal"
        ):
            return "prepare_proposal"
        return "identify_appointment"

    workflow.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "identify_appointment": "identify_appointment",
            "prepare_proposal": "prepare_proposal",
            "end": END,
        },
    )

    def route_appointment(
        state: AppointmentCancellationState,
    ) -> Literal["prepare_proposal", "agent", "end"]:
        if state.get("error"):
            return "end"
        if state.get("appointment_id"):
            return "prepare_proposal"
        return "agent"

    workflow.add_conditional_edges(
        "identify_appointment",
        route_appointment,
        {"prepare_proposal": "prepare_proposal", "agent": "agent", "end": END},
    )

    def route_proposal(
        state: AppointmentCancellationState,
    ) -> Literal["atomic_cancel", "agent", "end"]:
        if state.get("approval_status") == "APPROVED":
            return "atomic_cancel"
        if state.get("cancellation_proposal"):
            return "end"
        return "agent"

    workflow.add_conditional_edges(
        "prepare_proposal",
        route_proposal,
        {"atomic_cancel": "atomic_cancel", "agent": "agent", "end": END},
    )

    def cancellation_should_continue_router(
        state: AppointmentCancellationState,
    ) -> Literal["tools", "end"]:
        if state.get("error") or state.get("cancellation_proposal"):
            return "end"
        messages = state.get("messages", [])
        if not messages:
            return "end"
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        return "end"

    workflow.add_conditional_edges(
        "agent", cancellation_should_continue_router, {"tools": "tools", "end": END}
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("atomic_cancel", END)

    return workflow.compile()
