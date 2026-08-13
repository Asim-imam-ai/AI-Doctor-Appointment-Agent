"""LangGraph Appointment Booking Agent with HITL Workflow (Phase 5)."""

import logging
from typing import Any, Dict, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import AppointmentBookingState
from app.core.config import settings
from app.core.prompts import BOOKING_SYSTEM_PROMPT
from app.schemas.booking_agent import BookingProposal
from app.tools import BOOKING_PREPARE_TOOLS
from app.tools.booking_proposal import (
    create_booking_proposal,
    execute_atomic_booking,
)

logger = logging.getLogger(__name__)

# Out-of-scope & Unsupported keyword filters
CANCELLATION_MUTATION_KEYWORDS = ["cancel", "cancellation", "drop appointment"]
RESCHEDULE_MUTATION_KEYWORDS = ["reschedule", "change time", "move appointment"]
MEDICAL_DIAGNOSIS_KEYWORDS = [
    "diagnose",
    "diagnosis",
    "symptom",
    "pain",
    "treatment",
    "medicine",
    "cure",
]


def classify_booking_intent_node(
    state: AppointmentBookingState,
) -> Dict[str, Any]:
    """Node: Validate request and classify intent vs medical/cancellation requests."""
    msg = state.get("user_message", "").strip().lower()

    # Check for medical diagnosis
    if any(kw in msg for kw in MEDICAL_DIAGNOSIS_KEYWORDS):
        logger.info("Classified intent as OUT_OF_SCOPE (medical advice/diagnosis)")
        return {
            "intent": "OUT_OF_SCOPE",
            "response": (
                "I am an appointment booking assistant and cannot provide medical "
                "diagnoses, symptom evaluations, or treatment advice. Please consult "
                "a qualified healthcare provider."
            ),
        }

    # Check for cancellation or rescheduling request
    if any(
        kw in msg
        for kw in CANCELLATION_MUTATION_KEYWORDS + RESCHEDULE_MUTATION_KEYWORDS
    ):
        logger.info(
            "Classified intent as UNSUPPORTED (cancellation/reschedule requested)"
        )
        return {
            "intent": "UNSUPPORTED",
            "response": (
                "The Booking Agent does not support cancelling or rescheduling "
                "appointments in this phase."
            ),
        }

    return {"intent": "BOOKING_REQUEST"}


def prepare_proposal_node(
    state: AppointmentBookingState,
) -> Dict[str, Any]:
    """Node: Prepares a BookingProposal if patient, doctor, and slot IDs exist."""
    patient_id = state.get("patient_id")
    doctor_id = state.get("doctor_id")
    slot_id = state.get("slot_id")

    if not patient_id or not doctor_id or not slot_id:
        return {}

    try:
        proposal = create_booking_proposal(
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_id=slot_id,
            user_timezone=state.get("user_timezone", "UTC"),
            reason=state.get("reason"),
        )
        return {
            "booking_proposal": proposal,
            "approval_status": "PENDING",
            "proposal_version": proposal.proposal_version,
            "response": (
                f"Booking proposal prepared for {proposal.doctor_name} on "
                f"{proposal.start_time.strftime('%Y-%m-%d %H:%M UTC')}. "
                f"Requires approval (Request ID: {proposal.booking_request_id})."
            ),
        }
    except Exception as e:
        logger.error(f"Error preparing booking proposal: {e}")
        return {
            "error": f"Proposal preparation failed: {str(e)}",
            "response": f"Could not prepare booking proposal: {str(e)}",
        }


def booking_agent_node(
    state: AppointmentBookingState,
    llm: Optional[BaseChatModel] = None,
) -> Dict[str, Any]:
    """Node: LLM invocation node for preparing proposal when IDs are missing."""
    if state.get("booking_proposal"):
        return {}

    iteration = state.get("iteration_count", 0) + 1
    max_iterations = getattr(settings, "MAX_AGENT_ITERATIONS", 5)

    if iteration > max_iterations:
        return {
            "iteration_count": iteration,
            "error": "Agent iteration limit reached.",
            "response": "Could not complete booking preparation within allowed steps.",
        }

    messages = list(state.get("messages", []))
    if not messages and state.get("user_message"):
        user_tz = state.get("user_timezone", "UTC")
        sys_prompt = f"{BOOKING_SYSTEM_PROMPT}\nUser Timezone: {user_tz}"
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=state["user_message"]),
        ]

    if llm is None:
        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=settings.OPENAI_MODEL,
                api_key=settings.OPENAI_API_KEY or "dummy-key-for-test",
                temperature=0.0,
            )
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return {
                "error": "LLM initialization failed",
                "response": "Booking assistant is currently unavailable.",
            }

    bound_llm = llm.bind_tools(BOOKING_PREPARE_TOOLS)

    try:
        response_msg = bound_llm.invoke(messages)
        messages.append(response_msg)
        return {
            "messages": messages,
            "iteration_count": iteration,
            "response": (
                response_msg.content
                if isinstance(response_msg.content, str)
                else str(response_msg.content)
            ),
        }
    except Exception as e:
        logger.error(f"LLM execution error in booking agent: {e}")
        return {
            "error": f"LLM execution failed: {str(e)}",
            "response": "An error occurred while preparing your booking proposal.",
        }


def booking_tool_execution_node(
    state: AppointmentBookingState,
) -> Dict[str, Any]:
    """Node: Pre-approval tool execution for slot search and proposal creation."""
    messages = list(state.get("messages", []))
    tool_call_count = state.get("tool_call_count", 0)
    last_msg = messages[-1] if messages else None

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_calls = last_msg.tool_calls
    proposal_created: Optional[BookingProposal] = None

    for tool_call in tool_calls:
        tool_call_count += 1
        tool_name = tool_call["name"]
        args = tool_call.get("args", {})

        if tool_name == "prepare_booking_proposal_tool":
            from app.tools.booking_proposal import prepare_booking_proposal_tool

            try:
                output_str = prepare_booking_proposal_tool.invoke(args)
                # Attempt to parse created proposal back into state
                p_dict = BookingProposal.model_validate_json(output_str)
                proposal_created = p_dict
            except Exception as e:
                output_str = f'{{"error": "Failed to prepare proposal: {str(e)}"}}'
        elif tool_name == "search_available_slots":
            from app.tools.availability_search import search_available_slots_tool

            try:
                output_str = search_available_slots_tool.invoke(args)
            except Exception as e:
                output_str = f'{{"error": "Tool execution failed: {str(e)}"}}'
        elif tool_name == "search_doctors":
            from app.tools.doctor_search import search_doctors_tool

            try:
                output_str = search_doctors_tool.invoke(args)
            except Exception as e:
                output_str = f'{{"error": "Tool execution failed: {str(e)}"}}'
        elif tool_name == "get_doctor_details":
            from app.tools.doctor_search import get_doctor_details_tool

            try:
                output_str = get_doctor_details_tool.invoke(args)
            except Exception as e:
                output_str = f'{{"error": "Tool execution failed: {str(e)}"}}'
        else:
            output_str = '{"error": "Unauthorized tool call."}'

        messages.append(ToolMessage(content=output_str, tool_call_id=tool_call["id"]))

    res_dict: Dict[str, Any] = {
        "messages": messages,
        "tool_call_count": tool_call_count,
    }
    if proposal_created:
        res_dict["booking_proposal"] = proposal_created
        res_dict["approval_status"] = "PENDING"
        res_dict["proposal_version"] = proposal_created.proposal_version

    return res_dict


def post_approval_atomic_booking_node(
    state: AppointmentBookingState,
) -> Dict[str, Any]:
    """Node: Executes slot revalidation and atomic booking AFTER approval."""
    proposal = state.get("booking_proposal")
    approval_status = state.get("approval_status")

    if not proposal or approval_status != "APPROVED":
        return {
            "error": "Cannot execute booking without explicit HITL approval.",
            "response": "Booking aborted: explicit approval was not provided.",
        }

    res = execute_atomic_booking(
        booking_request_id=proposal.booking_request_id,
        proposal_version=state.get("proposal_version", 1),
        patient_id=state.get("patient_id") or proposal.patient_id,
    )

    return {
        "booking_result": res,
        "response": res.message,
    }


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
