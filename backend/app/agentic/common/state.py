"""Shared LangGraph state fields used by independent workflow state contracts."""

from typing import Annotated, Any
from uuid import UUID

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class CommonAgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    user_message: str
    patient_id: UUID
    conversation_id: UUID
    memory_context: list[dict[str, Any]]
    summary: str
    intent: str
    response: str
    error: str
    iteration_count: int
    tool_call_count: int
    metadata: dict[str, Any]
