"""Cancellation graph state."""

from typing import Any, Optional
from uuid import UUID

from app.agentic.common.state import CommonAgentState
from app.api.schemas.management_agent import CancellationProposal, CancellationResult


class AppointmentCancellationState(CommonAgentState, total=False):
    appointment_id: Optional[UUID]
    user_timezone: str
    reason: Optional[str]
    cancellation_proposal: Optional[CancellationProposal]
    approval_status: Optional[str]
    proposal_version: int
    cancellation_result: Optional[CancellationResult]
    matching_appointments: Optional[list[dict[str, Any]]]
