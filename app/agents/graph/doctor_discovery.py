"""LangGraph Doctor Discovery Agent Graph Workflow."""

from typing import Any, Literal, Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

# Out-of-scope / Unsupported intent patterns
from app.agents.nodes.doctor_discovery import (
    agent_reasoning_node,
    classify_intent_node,
    tool_execution_node,
)
from app.agents.state import DoctorDiscoveryState


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
            "POLICY_QUESTION",
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
