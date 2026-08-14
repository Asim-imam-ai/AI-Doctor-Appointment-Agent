"""LangGraph Appointment Cancellation Agent with HITL Workflow (Phase 6)."""

import logging
from typing import Any, Dict, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import AppointmentCancellationState
from app.core.config import settings
from app.core.prompts import CANCELLATION_SYSTEM_PROMPT
from app.guardrails import GuardrailPipeline
from app.schemas.management_agent import CancellationProposal
from app.services import AppointmentService
from app.tools import CANCELLATION_PREPARE_TOOLS
from app.tools.management_proposal import (
    create_cancellation_proposal,
    execute_atomic_cancellation,
)

logger = logging.getLogger(__name__)

MEDICAL_DIAGNOSIS_KEYWORDS = [
    "diagnose",
    "diagnosis",
    "symptom",
    "pain",
    "treatment",
    "medicine",
    "cure",
]


def classify_cancellation_intent_node(
    state: AppointmentCancellationState,
) -> Dict[str, Any]:
    """Node: Classifies request intent and checks safety boundaries using GuardrailPipeline."""
    msg = state.get("user_message", "").strip()

    decision = GuardrailPipeline.run_input_pipeline(msg)
    if not decision.allowed:
        logger.info(
            f"Guardrail intercepted cancellation request: {decision.reason_code}"
        )
        return {
            "intent": decision.category.value,
            "response": decision.user_message,
        }

    return {"intent": "CANCEL_APPOINTMENT"}


def identify_and_authorize_appointment_node(
    state: AppointmentCancellationState,
) -> Dict[str, Any]:
    """Node: Identifies authorized appointments for patient and validates eligibility."""
    patient_id = state.get("patient_id")
    appointment_id = state.get("appointment_id")

    if not patient_id:
        return {
            "error": "Patient ID required for authorization.",
            "response": "Authentication required to cancel an appointment.",
        }

    appt_service = AppointmentService()
    try:
        user_appts = appt_service.list_patient_appointments(patient_id)
        # Filter active non-cancelled appointments
        active_appts = [
            a
            for a in user_appts
            if str(a.status.value).upper() not in ("CANCELLED", "COMPLETED", "EXPIRED")
        ]

        if appointment_id:
            try:
                target = appt_service.get_appointment(appointment_id)
                if not target or target.patient_id != patient_id:
                    return {
                        "error": f"Unauthorized: appointment '{appointment_id}' does not belong to user or does not exist.",
                        "response": f"Could not find active appointment matching ID '{appointment_id}'.",
                    }
                appt_service.check_cancellation_eligibility(target.id, patient_id)
                return {
                    "appointment_id": target.id,
                    "matching_appointments": [target.model_dump(mode="json")],
                }
            except ValueError as ve:
                return {
                    "appointment_id": None,
                    "error": str(ve),
                    "response": f"Appointment cannot be cancelled: {str(ve)}",
                }

        if not active_appts:
            return {
                "error": "No active appointments found for user.",
                "response": "You currently have no active appointments to cancel.",
            }

        # Multiple active appointments found
        if len(active_appts) > 1:
            appts_data = [a.model_dump(mode="json") for a in active_appts]
            prompt_list = "\n".join(
                [
                    f"{idx + 1}. ID: {a.id} — Start: {a.start_time.strftime('%Y-%m-%d %H:%M UTC')}"
                    for idx, a in enumerate(active_appts)
                ]
            )
            return {
                "matching_appointments": appts_data,
                "response": (
                    f"You have multiple active appointments:\n{prompt_list}\n"
                    "Please specify which appointment ID you would like to cancel."
                ),
            }

        # Exactly 1 active appointment
        single_target = active_appts[0]
        try:
            appt_service.check_cancellation_eligibility(single_target.id, patient_id)
            return {
                "appointment_id": single_target.id,
                "matching_appointments": [single_target.model_dump(mode="json")],
            }
        except ValueError as ve:
            return {
                "error": str(ve),
                "response": f"Appointment cannot be cancelled: {str(ve)}",
            }

    except Exception as e:
        logger.error(f"Error identifying appointment: {e}")
        return {
            "error": f"Failed to identify appointment: {str(e)}",
            "response": "Error looking up your appointments.",
        }


def prepare_cancellation_proposal_node(
    state: AppointmentCancellationState,
) -> Dict[str, Any]:
    """Node: Prepares a structured CancellationProposal requiring HITL approval."""
    patient_id = state.get("patient_id")
    appointment_id = state.get("appointment_id")

    if not patient_id or not appointment_id or state.get("error"):
        return {}

    try:
        proposal = create_cancellation_proposal(
            appointment_id=appointment_id,
            patient_id=patient_id,
            reason=state.get("reason"),
            user_timezone=state.get("user_timezone", "UTC"),
        )
        return {
            "cancellation_proposal": proposal,
            "approval_status": "PENDING",
            "proposal_version": proposal.proposal_version,
            "response": (
                f"Cancellation proposal prepared for appointment on "
                f"{proposal.appointment_start.strftime('%Y-%m-%d %H:%M UTC')}. "
                f"Requires explicit approval (Request ID: {proposal.cancellation_request_id})."
            ),
        }
    except Exception as e:
        logger.error(f"Error preparing cancellation proposal: {e}")
        return {
            "error": f"Cancellation proposal preparation failed: {str(e)}",
            "response": f"Could not prepare cancellation proposal: {str(e)}",
        }


def cancellation_agent_node(
    state: AppointmentCancellationState,
    llm: Optional[BaseChatModel] = None,
) -> Dict[str, Any]:
    """Node: LLM invocation node if appointment selection or tool usage is needed."""
    if state.get("cancellation_proposal") or state.get("error"):
        return {}

    iteration = state.get("iteration_count", 0) + 1
    max_iterations = getattr(settings, "MAX_AGENT_ITERATIONS", 5)

    if iteration > max_iterations:
        return {
            "iteration_count": iteration,
            "error": "Agent iteration limit reached.",
            "response": "Could not complete cancellation preparation within allowed steps.",
        }

    messages = list(state.get("messages", []))
    if not messages and state.get("user_message"):
        user_tz = state.get("user_timezone", "UTC")
        sys_prompt = f"{CANCELLATION_SYSTEM_PROMPT}\nUser Timezone: {user_tz}"
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
                "response": "Cancellation assistant is currently unavailable.",
            }

    bound_llm = llm.bind_tools(CANCELLATION_PREPARE_TOOLS)

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
        logger.error(f"LLM execution error in cancellation agent: {e}")
        return {
            "error": f"LLM execution failed: {str(e)}",
            "response": "An error occurred while preparing your cancellation request.",
        }


def cancellation_tool_execution_node(
    state: AppointmentCancellationState,
) -> Dict[str, Any]:
    """Node: Pre-approval tool execution for proposal creation."""
    messages = list(state.get("messages", []))
    tool_call_count = state.get("tool_call_count", 0)
    last_msg = messages[-1] if messages else None

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_calls = last_msg.tool_calls
    proposal_created: Optional[CancellationProposal] = None

    for tool_call in tool_calls:
        tool_call_count += 1
        tool_name = tool_call["name"]
        args = tool_call.get("args", {})

        if tool_name == "prepare_cancellation_proposal_tool":
            from app.tools.management_proposal import prepare_cancellation_proposal_tool

            try:
                output_str = prepare_cancellation_proposal_tool.invoke(args)
                proposal_created = CancellationProposal.model_validate_json(output_str)
            except Exception as e:
                output_str = f'{{"error": "Failed to prepare proposal: {str(e)}"}}'
        elif tool_name == "list_user_appointments_tool":
            from app.tools.management_proposal import list_user_appointments_tool

            try:
                output_str = list_user_appointments_tool.invoke(args)
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
        res_dict["cancellation_proposal"] = proposal_created
        res_dict["approval_status"] = "PENDING"
        res_dict["proposal_version"] = proposal_created.proposal_version

    return res_dict


def post_approval_atomic_cancellation_node(
    state: AppointmentCancellationState,
) -> Dict[str, Any]:
    """Node: Revalidates policy and executes atomic cancellation AFTER explicit HITL approval."""
    proposal = state.get("cancellation_proposal")
    approval_status = state.get("approval_status")

    if not proposal or approval_status != "APPROVED":
        return {
            "error": "Cannot execute cancellation without explicit HITL approval.",
            "response": "Cancellation aborted: explicit approval was not provided.",
        }

    res = execute_atomic_cancellation(
        cancellation_request_id=proposal.cancellation_request_id,
        proposal_version=state.get("proposal_version", 1),
        patient_id=state.get("patient_id") or proposal.patient_id,
    )

    return {
        "cancellation_result": res,
        "response": res.message,
    }


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
