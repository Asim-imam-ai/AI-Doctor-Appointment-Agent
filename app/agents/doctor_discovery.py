"""LangGraph Doctor Discovery Agent Graph Workflow."""

import logging
from typing import Any, Dict, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import END, START, StateGraph

from app.agents.state import DoctorDiscoveryState
from app.core.config import settings
from app.core.prompts import DOCTOR_DISCOVERY_SYSTEM_PROMPT
from app.guardrails import GuardrailCategory, GuardrailPipeline
from app.schemas.doctor_discovery import DoctorSearchCriteria, DoctorSearchResult
from app.tools import DOCTOR_DISCOVERY_TOOLS
from app.tools.doctor_search import execute_doctor_search

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

    # Check for booking/cancellation/rescheduling request
    lower_msg = msg.lower()
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
            from app.repositories import get_memory_repository
            from app.services.memory_service import MemoryService

            mem_service = MemoryService(get_memory_repository())
            memories = mem_service.get_user_memories(patient_id)

        from app.services.context_builder import ContextBuilder

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
        args = tool_call.get("args", {})

        if tool_name == "search_doctors":
            try:
                criteria = DoctorSearchCriteria(**args)
                tool_results_data = execute_doctor_search(criteria)
                output_str = tool_results_data.model_dump_json()
            except Exception as e:
                output_str = f'{{"error": "Tool execution failed: {str(e)}"}}'
        elif tool_name == "get_doctor_details":
            from app.tools.doctor_search import get_doctor_details_tool

            try:
                output_str = get_doctor_details_tool.invoke(args)
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


def should_continue_router(state: DoctorDiscoveryState) -> Literal["tools", "end"]:
    """Conditional Edge Router: Decide whether to execute tools or end workflow."""
    intent = state.get("intent")
    if intent in ("OUT_OF_SCOPE", "UNSUPPORTED"):
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


def build_doctor_discovery_graph(llm: Optional[BaseChatModel] = None) -> Any:
    """Build and compile the LangGraph Doctor Discovery workflow graph."""
    workflow = StateGraph(DoctorDiscoveryState)

    workflow.add_node("classify_intent", classify_intent_node)

    # Use partial wrapper for agent reasoning if custom LLM is injected
    def agent_node(state: DoctorDiscoveryState):
        return agent_reasoning_node(state, llm=llm)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_execution_node)

    workflow.add_edge(START, "classify_intent")

    def route_intent(state: DoctorDiscoveryState) -> Literal["agent", "end"]:
        if state.get("intent") in (
            "OUT_OF_SCOPE",
            "UNSUPPORTED",
            "PROMPT_INJECTION",
            "INVALID_INPUT",
        ):
            return "end"
        return "agent"

    workflow.add_conditional_edges(
        "classify_intent", route_intent, {"agent": "agent", "end": END}
    )
    workflow.add_conditional_edges(
        "agent", should_continue_router, {"tools": "tools", "end": END}
    )
    workflow.add_edge("tools", "agent")

    return workflow.compile()
