"""Booking graph state."""

from typing import Optional
from uuid import UUID

from app.agentic.common.state import CommonAgentState
from app.api.schemas.booking_agent import BookingProposal, BookingResult


class AppointmentBookingState(CommonAgentState, total=False):
    doctor_id: Optional[UUID]
    slot_id: Optional[UUID]
    user_timezone: str
    reason: Optional[str]
    booking_proposal: Optional[BookingProposal]
    approval_status: Optional[str]
    proposal_version: int
    booking_result: Optional[BookingResult]
