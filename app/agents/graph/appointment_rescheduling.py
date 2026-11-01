"""LangGraph Appointment Rescheduling Agent with HITL Workflow (Phase 6)."""

from typing import Any, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.agents.nodes.appointment_rescheduling import (
    classify_rescheduling_intent_node,
    find_replacement_slots_node,
    identify_and_authorize_old_appointment_node,
    post_approval_atomic_rescheduling_node,
    prepare_rescheduling_proposal_node,
    rescheduling_agent_node,
    rescheduling_tool_execution_node,
)
from app.agents.state import AppointmentReschedulingState


def build_appointment_rescheduling_graph(llm: Optional[BaseChatModel] = None) -> Any:
    """Build and compile the LangGraph Appointment Rescheduling workflow graph."""
    workflow = StateGraph(AppointmentReschedulingState)

    workflow.add_node("classify_intent", classify_rescheduling_intent_node)
    workflow.add_node(
        "identify_appointment", identify_and_authorize_old_appointment_node
    )
    workflow.add_node("find_slots", find_replacement_slots_node)
    workflow.add_node("prepare_proposal", prepare_rescheduling_proposal_node)

    def agent_node(state: AppointmentReschedulingState):
        return rescheduling_agent_node(state, llm=llm)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", rescheduling_tool_execution_node)
    workflow.add_node("atomic_reschedule", post_approval_atomic_rescheduling_node)

    workflow.add_edge(START, "classify_intent")

    def route_intent(
        state: AppointmentReschedulingState,
    ) -> Literal["identify_appointment", "prepare_proposal", "end"]:
        if state.get("intent") == "OUT_OF_SCOPE":
            return "end"
        if state.get("approval_status") == "APPROVED" or state.get(
            "rescheduling_proposal"
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
        state: AppointmentReschedulingState,
    ) -> Literal["find_slots", "agent", "end"]:
        if state.get("error"):
            return "end"
        if state.get("appointment_id"):
            return "find_slots"
        return "agent"

    workflow.add_conditional_edges(
        "identify_appointment",
        route_appointment,
        {"find_slots": "find_slots", "agent": "agent", "end": END},
    )

    def route_slots(
        state: AppointmentReschedulingState,
    ) -> Literal["prepare_proposal", "agent", "end"]:
        if state.get("error"):
            return "end"
        if state.get("new_slot_id"):
            return "prepare_proposal"
        return "agent"

    workflow.add_conditional_edges(
        "find_slots",
        route_slots,
        {"prepare_proposal": "prepare_proposal", "agent": "agent", "end": END},
    )

    def route_proposal(
        state: AppointmentReschedulingState,
    ) -> Literal["atomic_reschedule", "agent", "end"]:
        if state.get("approval_status") == "APPROVED":
            return "atomic_reschedule"
        if state.get("rescheduling_proposal"):
            return "end"
        return "agent"

    workflow.add_conditional_edges(
        "prepare_proposal",
        route_proposal,
        {"atomic_reschedule": "atomic_reschedule", "agent": "agent", "end": END},
    )

    def rescheduling_should_continue_router(
        state: AppointmentReschedulingState,
    ) -> Literal["tools", "end"]:
        if state.get("error") or state.get("rescheduling_proposal"):
            return "end"
        messages = state.get("messages", [])
        if not messages:
            return "end"
        last_msg = messages[-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            return "tools"
        return "end"

    workflow.add_conditional_edges(
        "agent", rescheduling_should_continue_router, {"tools": "tools", "end": END}
    )

    workflow.add_edge("tools", "agent")
    workflow.add_edge("atomic_reschedule", END)

    return workflow.compile()
