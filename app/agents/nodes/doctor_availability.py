"""LangGraph Doctor Availability Agent Graph Workflow (Phase 4)."""

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.agents.state import DoctorAvailabilityState
from app.core.config import settings
from app.core.prompts import AVAILABILITY_SYSTEM_PROMPT
from app.schemas.availability_agent import (
    AvailabilitySearchCriteria,
    AvailabilitySearchResult,
)
from app.tools import AVAILABILITY_TOOLS
from app.tools.availability_search import execute_availability_search

logger = logging.getLogger(__name__)

# Out-of-scope & Unsupported keyword filters
BOOKING_MUTATION_KEYWORDS = ["book", "booking", "reserve", "confirm appointment"]
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


def classify_availability_intent_node(
    state: DoctorAvailabilityState,
) -> Dict[str, Any]:
    """Node: Validate request and classify intent vs mutation/medical requests."""
    msg = state.get("user_message", "").strip().lower()

    # Check for medical diagnosis
    if any(kw in msg for kw in MEDICAL_DIAGNOSIS_KEYWORDS):
        logger.info("Classified intent as OUT_OF_SCOPE (medical advice/diagnosis)")
        return {
            "intent": "OUT_OF_SCOPE",
            "response": (
                "I am an appointment availability assistant and cannot provide medical "
                "diagnoses, symptom evaluations, or treatment advice. Please consult "
                "a qualified healthcare provider or emergency service."
            ),
        }

    # Check for booking request
    if any(kw in msg for kw in BOOKING_MUTATION_KEYWORDS):
        logger.info("Classified intent as BOOKING_REQUEST (unsupported in Phase 4)")
        return {
            "intent": "BOOKING_REQUEST",
            "response": (
                "I can help you check available appointment slots, but I cannot "
                "complete a booking. Appointment booking requires Human-In-The-Loop "
                "(HITL) approval in a subsequent phase."
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
                "The Availability Agent is strictly read-only and cannot cancel "
                "or reschedule existing appointments."
            ),
        }

    return {"intent": "AVAILABILITY_SEARCH"}


def availability_agent_node(
    state: DoctorAvailabilityState,
    llm: Optional[BaseChatModel] = None,
) -> Dict[str, Any]:
    """Node: LLM invocation node for availability search with tool binding."""
    iteration = state.get("iteration_count", 0) + 1
    max_iterations = getattr(settings, "MAX_AGENT_ITERATIONS", 5)

    if iteration > max_iterations:
        logger.warning(
            f"Iteration count {iteration} exceeded MAX_AGENT_ITERATIONS "
            f"({max_iterations})."
        )
        return {
            "iteration_count": iteration,
            "error": "Agent iteration limit reached.",
            "response": (
                "I could not complete the availability search within the allowed steps."
            ),
        }

    messages = list(state.get("messages", []))
    if not messages and state.get("user_message"):
        user_tz = state.get("user_timezone", "UTC")
        sys_prompt = f"{AVAILABILITY_SYSTEM_PROMPT}\nUser Timezone: {user_tz}"
        messages = [
            SystemMessage(content=sys_prompt),
            HumanMessage(content=state["user_message"]),
        ]

    # Initialize LLM if not injected
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
                "response": "Doctor availability service is currently unavailable.",
            }

    bound_llm = llm.bind_tools(AVAILABILITY_TOOLS)

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
        logger.error(f"LLM execution error in availability agent: {e}")
        return {
            "error": f"LLM execution failed: {str(e)}",
            "response": (
                "An error occurred while processing your availability request."
            ),
        }


def availability_tool_execution_node(
    state: DoctorAvailabilityState,
) -> Dict[str, Any]:
    """Node: Deterministic execution of availability read-only tools."""
    messages = list(state.get("messages", []))
    tool_call_count = state.get("tool_call_count", 0)
    last_msg = messages[-1] if messages else None

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_calls = last_msg.tool_calls
    tool_results_data: Optional[AvailabilitySearchResult] = None

    for tool_call in tool_calls:
        tool_call_count += 1
        max_tool_calls = getattr(settings, "MAX_TOOL_CALLS", 10)
        if tool_call_count > max_tool_calls:
            logger.warning("Tool call limit exceeded in availability agent.")
            messages.append(
                ToolMessage(
                    content='{"error": "Tool execution limit exceeded."}',
                    tool_call_id=tool_call["id"],
                )
            )
            continue

        tool_name = tool_call["name"]
        args = tool_call.get("args", {})

        if tool_name == "search_available_slots":
            try:
                criteria = AvailabilitySearchCriteria(
                    user_timezone=state.get("user_timezone", "UTC"), **args
                )
                tool_results_data = execute_availability_search(criteria)
                output_str = tool_results_data.model_dump_json()
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

    return {
        "messages": messages,
        "tool_call_count": tool_call_count,
        "tool_results": tool_results_data,
    }
