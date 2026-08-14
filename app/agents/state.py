"""State schemas for Doctor Agent LangGraph Workflows."""

import uuid
from typing import Annotated, Any, Dict, List, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from app.schemas.availability_agent import (
    AvailabilitySearchCriteria,
    AvailabilitySearchResult,
)
from app.schemas.booking_agent import BookingProposal, BookingResult
from app.schemas.doctor_discovery import DoctorSearchCriteria, DoctorSearchResult
from app.schemas.management_agent import (
    CancellationProposal,
    CancellationResult,
    ReschedulingProposal,
    ReschedulingResult,
)


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
    intent: Optional[str]
    availability_criteria: Optional[AvailabilitySearchCriteria]
    tool_results: Optional[AvailabilitySearchResult]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]


class AppointmentBookingState(TypedDict):
    """Explicit state representation for Appointment Booking HITL Graph (Phase 5)."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    patient_id: uuid.UUID
    doctor_id: Optional[uuid.UUID]
    slot_id: Optional[uuid.UUID]
    user_timezone: str
    reason: Optional[str]
    intent: Optional[str]
    booking_proposal: Optional[BookingProposal]
    approval_status: Optional[str]  # e.g. "PENDING", "APPROVED", "REJECTED"
    proposal_version: int
    booking_result: Optional[BookingResult]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]


class AppointmentCancellationState(TypedDict):
    """Explicit state representation for Cancellation HITL Graph (Phase 6)."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    patient_id: uuid.UUID
    appointment_id: Optional[uuid.UUID]
    user_timezone: str
    reason: Optional[str]
    intent: Optional[str]
    cancellation_proposal: Optional[CancellationProposal]
    approval_status: Optional[str]  # e.g. "PENDING", "APPROVED", "REJECTED"
    proposal_version: int
    cancellation_result: Optional[CancellationResult]
    matching_appointments: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]


class AppointmentReschedulingState(TypedDict):
    """Explicit state representation for Rescheduling HITL Graph (Phase 6)."""

    messages: Annotated[List[BaseMessage], add_messages]
    user_message: str
    patient_id: uuid.UUID
    appointment_id: Optional[uuid.UUID]
    new_slot_id: Optional[uuid.UUID]
    user_timezone: str
    reason: Optional[str]
    intent: Optional[str]
    rescheduling_proposal: Optional[ReschedulingProposal]
    approval_status: Optional[str]  # e.g. "PENDING", "APPROVED", "REJECTED"
    proposal_version: int
    rescheduling_result: Optional[ReschedulingResult]
    matching_appointments: Optional[List[Dict[str, Any]]]
    available_slots: Optional[List[Dict[str, Any]]]
    response: Optional[str]
    error: Optional[str]
    iteration_count: int
    tool_call_count: int
    metadata: Dict[str, Any]
