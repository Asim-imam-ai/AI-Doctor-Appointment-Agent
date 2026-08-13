"""State schema for Doctor Discovery LangGraph Workflow."""

from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.schemas.doctor_discovery import DoctorSearchCriteria, DoctorSearchResult


class DoctorDiscoveryState(TypedDict):
    """Explicit state representation for Doctor Discovery Graph."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    intent: Optional[str]  # e.g. "DOCTOR_SEARCH", "UNSUPPORTED", "OUT_OF_SCOPE"
    search_criteria: Optional[DoctorSearchCriteria]
    tool_results: Optional[DoctorSearchResult]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]
