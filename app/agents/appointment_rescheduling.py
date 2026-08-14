"""LangGraph Appointment Rescheduling Agent with HITL Workflow (Phase 6)."""

import logging
from typing import Any, Dict, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import AppointmentReschedulingState
from app.core.config import settings
from app.core.prompts import RESCHEDULING_SYSTEM_PROMPT
from app.schemas.management_agent import ReschedulingProposal
from app.services import AppointmentService, AvailabilityService
from app.tools import RESCHEDULING_PREPARE_TOOLS
from app.tools.management_proposal import (
    create_rescheduling_proposal,
    execute_atomic_rescheduling,
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


def classify_rescheduling_intent_node(
    state: AppointmentReschedulingState,
) -> Dict[str, Any]:
    """Node: Classifies request intent and checks safety boundaries."""
    msg = state.get("user_message", "").strip().lower()

    if any(kw in msg for kw in MEDICAL_DIAGNOSIS_KEYWORDS):
        return {
            "intent": "OUT_OF_SCOPE",
            "response": (
                "I am an appointment rescheduling assistant and cannot provide medical "
                "diagnoses, symptom evaluations, or treatment advice. Please consult "
                "a qualified healthcare provider."
            ),
        }

    return {"intent": "RESCHEDULE_APPOINTMENT"}


def identify_and_authorize_old_appointment_node(
    state: AppointmentReschedulingState,
) -> Dict[str, Any]:
    """Node: Identifies existing authorized appointment to reschedule."""
    patient_id = state.get("patient_id")
    appointment_id = state.get("appointment_id")

    if not patient_id:
        return {
            "error": "Patient ID required for authorization.",
            "response": "Authentication required to reschedule an appointment.",
        }

    appt_service = AppointmentService()
    try:
        user_appts = appt_service.list_patient_appointments(patient_id)
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
                appt_service.check_reschedule_eligibility(target.id, patient_id)
                return {
                    "appointment_id": target.id,
                    "matching_appointments": [target.model_dump(mode="json")],
                }
            except ValueError as ve:
                return {
                    "appointment_id": None,
                    "error": str(ve),
                    "response": f"Appointment cannot be rescheduled: {str(ve)}",
                }

        if not active_appts:
            return {
                "error": "No active appointments found for user.",
                "response": "You currently have no active appointments to reschedule.",
            }

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
                    "Please specify which appointment ID you would like to reschedule."
                ),
            }

        single_target = active_appts[0]
        try:
            appt_service.check_reschedule_eligibility(single_target.id, patient_id)
            return {
                "appointment_id": single_target.id,
                "matching_appointments": [single_target.model_dump(mode="json")],
            }
        except ValueError as ve:
            return {
                "error": str(ve),
                "response": f"Appointment cannot be rescheduled: {str(ve)}",
            }

    except Exception as e:
        logger.error(f"Error identifying appointment to reschedule: {e}")
        return {
            "error": f"Failed to identify appointment: {str(e)}",
            "response": "Error looking up your appointments.",
        }


def find_replacement_slots_node(
    state: AppointmentReschedulingState,
) -> Dict[str, Any]:
    """Node: Uses Phase 4 AvailabilityService to list available replacement slots for doctor."""
    appointment_id = state.get("appointment_id")
    new_slot_id = state.get("new_slot_id")

    if not appointment_id or state.get("error"):
        return {}

    appt_service = AppointmentService()
    avail_service = AvailabilityService()

    try:
        appt = appt_service.get_appointment(appointment_id)
        if not appt:
            return {"error": "Appointment not found."}

        slots = avail_service.get_available_slots(appt.doctor_id)
        if not slots:
            return {
                "error": "No replacement available slots found for doctor.",
                "response": "Doctor currently has no open slots available for rescheduling.",
            }

        slots_data = [s.model_dump(mode="json") for s in slots]

        # If user hasn't explicitly chosen a slot, require exact slot selection
        if not new_slot_id:
            slot_list = "\n".join(
                [
                    f"{idx + 1}. Slot ID: {s.id} — Time: {s.start_time.strftime('%Y-%m-%d %H:%M UTC')}"
                    for idx, s in enumerate(slots)
                ]
            )
            return {
                "available_slots": slots_data,
                "response": (
                    f"Available replacement slots for your appointment:\n{slot_list}\n"
                    "Please reply with the exact Slot ID you would like to move your appointment to."
                ),
            }

        target_slot = next((s for s in slots if s.id == new_slot_id), None)
        if not target_slot:
            return {
                "error": f"Selected slot ID '{new_slot_id}' is not available.",
                "response": f"Slot '{new_slot_id}' is no longer available. Please select another slot.",
            }

        return {"available_slots": slots_data}

    except Exception as e:
        logger.error(f"Error finding replacement slots: {e}")
        return {
            "error": f"Failed to find replacement slots: {str(e)}",
            "response": "Could not search replacement slots.",
        }


def prepare_rescheduling_proposal_node(
    state: AppointmentReschedulingState,
) -> Dict[str, Any]:
    """Node: Prepares a structured ReschedulingProposal requiring HITL approval."""
    patient_id = state.get("patient_id")
    appointment_id = state.get("appointment_id")
    new_slot_id = state.get("new_slot_id")

    if not patient_id or not appointment_id or not new_slot_id or state.get("error"):
        return {}

    try:
        proposal = create_rescheduling_proposal(
            appointment_id=appointment_id,
            patient_id=patient_id,
            new_slot_id=new_slot_id,
            reason=state.get("reason"),
            user_timezone=state.get("user_timezone", "UTC"),
        )
        return {
            "rescheduling_proposal": proposal,
            "approval_status": "PENDING",
            "proposal_version": proposal.proposal_version,
            "response": (
                f"Rescheduling proposal prepared: move appointment to "
                f"{proposal.new_start_time.strftime('%Y-%m-%d %H:%M UTC')}. "
                f"Requires explicit approval (Request ID: {proposal.reschedule_request_id})."
            ),
        }
    except Exception as e:
        logger.error(f"Error preparing rescheduling proposal: {e}")
        return {
            "error": f"Rescheduling proposal preparation failed: {str(e)}",
            "response": f"Could not prepare rescheduling proposal: {str(e)}",
        }


def rescheduling_agent_node(
    state: AppointmentReschedulingState,
    llm: Optional[BaseChatModel] = None,
) -> Dict[str, Any]:
    """Node: LLM invocation node if selection or tool execution is needed."""
    if state.get("rescheduling_proposal") or state.get("error"):
        return {}

    iteration = state.get("iteration_count", 0) + 1
    max_iterations = getattr(settings, "MAX_AGENT_ITERATIONS", 5)

    if iteration > max_iterations:
        return {
            "iteration_count": iteration,
            "error": "Agent iteration limit reached.",
            "response": "Could not complete rescheduling preparation within allowed steps.",
        }

    messages = list(state.get("messages", []))
    if not messages and state.get("user_message"):
        user_tz = state.get("user_timezone", "UTC")
        sys_prompt = f"{RESCHEDULING_SYSTEM_PROMPT}\nUser Timezone: {user_tz}"
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
                "response": "Rescheduling assistant is currently unavailable.",
            }

    bound_llm = llm.bind_tools(RESCHEDULING_PREPARE_TOOLS)

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
        logger.error(f"LLM execution error in rescheduling agent: {e}")
        return {
            "error": f"LLM execution failed: {str(e)}",
            "response": "An error occurred while preparing your rescheduling request.",
        }


def rescheduling_tool_execution_node(
    state: AppointmentReschedulingState,
) -> Dict[str, Any]:
    """Node: Pre-approval tool execution for slot search and proposal creation."""
    messages = list(state.get("messages", []))
    tool_call_count = state.get("tool_call_count", 0)
    last_msg = messages[-1] if messages else None

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_calls = last_msg.tool_calls
    proposal_created: Optional[ReschedulingProposal] = None

    for tool_call in tool_calls:
        tool_call_count += 1
        tool_name = tool_call["name"]
        args = tool_call.get("args", {})

        if tool_name == "prepare_rescheduling_proposal_tool":
            from app.tools.management_proposal import prepare_rescheduling_proposal_tool

            try:
                output_str = prepare_rescheduling_proposal_tool.invoke(args)
                proposal_created = ReschedulingProposal.model_validate_json(output_str)
            except Exception as e:
                output_str = f'{{"error": "Failed to prepare proposal: {str(e)}"}}'
        elif tool_name == "search_available_slots":
            from app.tools.availability_search import search_available_slots_tool

            try:
                output_str = search_available_slots_tool.invoke(args)
            except Exception as e:
                output_str = f'{{"error": "Tool execution failed: {str(e)}"}}'
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
        res_dict["rescheduling_proposal"] = proposal_created
        res_dict["approval_status"] = "PENDING"
        res_dict["proposal_version"] = proposal_created.proposal_version

    return res_dict


def post_approval_atomic_rescheduling_node(
    state: AppointmentReschedulingState,
) -> Dict[str, Any]:
    """Node: Revalidates old appointment & new slot, executes atomic reschedule AFTER HITL approval."""
    proposal = state.get("rescheduling_proposal")
    approval_status = state.get("approval_status")

    if not proposal or approval_status != "APPROVED":
        return {
            "error": "Cannot execute rescheduling without explicit HITL approval.",
            "response": "Rescheduling aborted: explicit approval was not provided.",
        }

    res = execute_atomic_rescheduling(
        reschedule_request_id=proposal.reschedule_request_id,
        proposal_version=state.get("proposal_version", 1),
        patient_id=state.get("patient_id") or proposal.patient_id,
    )

    return {
        "rescheduling_result": res,
        "response": res.message,
    }


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
