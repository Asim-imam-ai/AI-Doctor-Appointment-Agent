"""State schemas for Doctor Agent LangGraph Workflows."""

from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.schemas.availability_agent import (
    AvailabilitySearchCriteria,
    AvailabilitySearchResult,
)
from app.schemas.doctor_discovery import DoctorSearchCriteria, DoctorSearchResult


class DoctorDiscoveryState(TypedDict):
    """Explicit state representation for Doctor Discovery Graph (Phase 3)."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    intent: Optional[str]
    search_criteria: Optional[DoctorSearchCriteria]
    tool_results: Optional[DoctorSearchResult]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]


class DoctorAvailabilityState(TypedDict):
    """Explicit state representation for Doctor Availability Graph (Phase 4)."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    user_timezone: str
    intent: Optional[
        str
    ]  # e.g. "AVAILABILITY_SEARCH", "BOOKING_REQUEST", "UNSUPPORTED", "OUT_OF_SCOPE"
    availability_criteria: Optional[AvailabilitySearchCriteria]
    tool_results: Optional[AvailabilitySearchResult]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]
