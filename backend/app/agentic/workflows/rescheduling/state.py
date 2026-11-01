"""Rescheduling graph state."""

from typing import Any, Optional
from uuid import UUID

from app.agentic.common.state import CommonAgentState
from app.api.schemas.management_agent import ReschedulingProposal, ReschedulingResult


class AppointmentReschedulingState(CommonAgentState, total=False):
    appointment_id: Optional[UUID]
    new_slot_id: Optional[UUID]
    user_timezone: str
    reason: Optional[str]
    rescheduling_proposal: Optional[ReschedulingProposal]
    approval_status: Optional[str]
    proposal_version: int
    rescheduling_result: Optional[ReschedulingResult]
    matching_appointments: Optional[list[dict[str, Any]]]
    available_slots: Optional[list[dict[str, Any]]]
