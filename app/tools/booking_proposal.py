"""Deterministic Read-Only Proposal Tool and Atomic Booking Execution for Phase 5."""

import uuid
from typing import Optional

from langchain_core.tools import tool

from app.services.booking_proposal import _PENDING_PROPOSALS as _PENDING_PROPOSALS

# Compatibility exports share the service's canonical proposal store.
from app.services.booking_proposal import (
    create_booking_proposal as create_booking_proposal,
)
from app.services.booking_proposal import (
    execute_atomic_booking as execute_atomic_booking,
)
from app.services.booking_proposal import get_pending_proposal as get_pending_proposal


@tool("prepare_booking_proposal_tool")
def prepare_booking_proposal_tool(
    patient_id: str,
    doctor_id: str,
    slot_id: str,
    user_timezone: str = "UTC",
    reason: Optional[str] = None,
) -> str:
    """Prepares a booking proposal requiring HITL approval before final mutation."""
    try:
        p_uuid = uuid.UUID(patient_id)
        d_uuid = uuid.UUID(doctor_id)
        s_uuid = uuid.UUID(slot_id)
        proposal = create_booking_proposal(
            patient_id=p_uuid,
            doctor_id=d_uuid,
            slot_id=s_uuid,
            user_timezone=user_timezone,
            reason=reason,
        )
        return proposal.model_dump_json()
    except Exception as e:
        return f'{{"error": "Failed to prepare booking proposal: {str(e)}"}}'
