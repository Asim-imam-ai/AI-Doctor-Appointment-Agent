"""LangGraph Doctor Discovery Agent Graph Workflow."""

import logging
from typing import Any, Dict, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage

from app.agentic.common.guardrails import GuardrailCategory, GuardrailPipeline
from app.agentic.common.tool_executor import (
    DOCTOR_DISCOVERY_TOOLS,
    execute_allowed_tool,
)
from app.agentic.workflows.doctor_discovery.prompts import (
    DOCTOR_DISCOVERY_SYSTEM_PROMPT,
)
from app.agentic.workflows.doctor_discovery.state import DoctorDiscoveryState
from app.api.schemas.doctor_discovery import DoctorSearchResult
from app.core.config import settings

logger = logging.getLogger(__name__)

# Out-of-scope / Unsupported intent patterns
UNSUPPORTED_APPOINTMENT_KEYWORDS = ["book", "booking", "cancel", "reschedule"]
MEDICAL_DIAGNOSIS_KEYWORDS = [
    "diagnose",
    "diagnosis",
    "symptom",
    "pain",
    "treatment",
    "medicine",
    "cure",
]


def classify_intent_node(state: DoctorDiscoveryState) -> Dict[str, Any]:
    """Node: Validate request and classify user message intent using GuardrailPipeline."""
    msg = state.get("user_message", "").strip()

    # Run security guardrail pipeline (Size, Injection, Jailbreak, Medical Scope)
    decision = GuardrailPipeline.run_input_pipeline(msg)
    if not decision.allowed:
        logger.info(f"Guardrail intercepted request: {decision.reason_code}")
        mapped_intent = (
            "OUT_OF_SCOPE"
            if decision.category
            in (
                GuardrailCategory.UNSAFE_MEDICAL_REQUEST,
                GuardrailCategory.JAILBREAK,
                GuardrailCategory.OUT_OF_SCOPE,
            )
            else decision.category.value
        )
        return {
            "intent": mapped_intent,
            "response": decision.user_message,
        }

    # Check for policy/knowledge questions
    lower_msg = msg.lower()
    policy_keywords = [
        "policy",
        "hours",
        "cancellation rule",
        "booking rule",
        "faq",
        "preparation",
    ]
    if any(kw in lower_msg for kw in policy_keywords):
        from app.infrastructure.db.services import get_rag_service

        rag = get_rag_service()
        result = rag.answer_query(msg)
        return {
            "intent": "POLICY_QUESTION",
            "response": result.answer,
        }

    # Check for booking/cancellation/rescheduling request
    if any(kw in lower_msg for kw in UNSUPPORTED_APPOINTMENT_KEYWORDS):
        logger.info("Classified intent as UNSUPPORTED (appointment mutation requested)")
        return {
            "intent": "UNSUPPORTED",
            "response": (
                "The Doctor Discovery Agent is currently in read-only mode and "
                "cannot book, cancel, or reschedule appointments. Booking workflows "
                "will be available in a subsequent phase."
            ),
        }

    return {"intent": "DOCTOR_SEARCH"}


def agent_reasoning_node(
    state: DoctorDiscoveryState,
    llm: Optional[BaseChatModel] = None,
) -> Dict[str, Any]:
    """Node: LLM invocation node with tool binding."""
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
                "I could not complete the doctor search within the allowed steps."
            ),
        }

    messages = list(state.get("messages", []))
    if not messages and state.get("user_message"):
        patient_id = state.get("patient_id")
        memories = []
        if patient_id:
            from app.infrastructure.db.repositories import get_memory_repository
            from app.memory.preferences import MemoryService

            mem_service = MemoryService(get_memory_repository())
            memories = mem_service.get_user_memories(patient_id)

        from app.memory.context_builder import ContextBuilder

        messages = ContextBuilder.prepare_bounded_messages(
            system_prompt=DOCTOR_DISCOVERY_SYSTEM_PROMPT,
            user_message=state["user_message"],
            history=[],
            summary=state.get("summary"),
            memories=memories,
        )

    # Initialize LLM if not injected
    if llm is None:
        try:
            from app.agentic.common.llm_runtime import get_chat_model

            llm = get_chat_model()
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            return {
                "error": "LLM initialization failed",
                "response": "Doctor search service is currently unavailable.",
            }

    bound_llm = llm.bind_tools(DOCTOR_DISCOVERY_TOOLS)

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
        logger.error(f"LLM execution error: {e}")
        return {
            "error": f"LLM execution failed: {str(e)}",
            "response": (
                "An error occurred while processing your doctor search request."
            ),
        }


def tool_execution_node(state: DoctorDiscoveryState) -> Dict[str, Any]:
    """Node: Deterministic execution of requested read-only discovery tools."""
    messages = list(state.get("messages", []))
    tool_call_count = state.get("tool_call_count", 0)
    last_msg = messages[-1] if messages else None

    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return {}

    tool_calls = last_msg.tool_calls
    tool_results_data: Optional[DoctorSearchResult] = None

    for tool_call in tool_calls:
        tool_call_count += 1
        max_tool_calls = getattr(settings, "MAX_TOOL_CALLS", 10)
        if tool_call_count > max_tool_calls:
            logger.warning("Tool call limit exceeded.")
            messages.append(
                ToolMessage(
                    content='{"error": "Tool execution limit exceeded."}',
                    tool_call_id=tool_call["id"],
                )
            )
            continue

        tool_name = tool_call["name"]

        if tool_name == "search_doctors":
            try:
                output_str = execute_allowed_tool(tool_call, DOCTOR_DISCOVERY_TOOLS)
                if not output_str.startswith('{"error"'):
                    tool_results_data = DoctorSearchResult.model_validate_json(
                        output_str
                    )
            except Exception:
                output_str = '{"error": "Tool execution failed."}'
        elif tool_name == "get_doctor_details":
            try:
                output_str = execute_allowed_tool(tool_call, DOCTOR_DISCOVERY_TOOLS)
            except Exception as e:
                output_str = f'{{"error": "Tool execution failed: {str(e)}"}}'
        else:
            output_str = '{"error": "Unauthorized or unknown tool called."}'

        messages.append(ToolMessage(content=output_str, tool_call_id=tool_call["id"]))

    return {
        "messages": messages,
        "tool_call_count": tool_call_count,
        "tool_results": tool_results_data,
    }
