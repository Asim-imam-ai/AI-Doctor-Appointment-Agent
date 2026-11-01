"""Deterministic proposal tool and atomic execution for Cancellation and Rescheduling (Phase 6)."""

import uuid
from typing import Optional

from langchain_core.tools import tool

from app.services import (
    AppointmentService,
)
from app.services.management_proposal import (
    _PENDING_CANCELLATION_PROPOSALS as _PENDING_CANCELLATION_PROPOSALS,
)
from app.services.management_proposal import (
    _PENDING_RESCHEDULING_PROPOSALS as _PENDING_RESCHEDULING_PROPOSALS,
)

# Global in-memory storage for pending cancellation and rescheduling proposals
from app.services.management_proposal import (
    create_cancellation_proposal as create_cancellation_proposal,
)
from app.services.management_proposal import (
    create_rescheduling_proposal as create_rescheduling_proposal,
)
from app.services.management_proposal import (
    execute_atomic_cancellation as execute_atomic_cancellation,
)
from app.services.management_proposal import (
    execute_atomic_rescheduling as execute_atomic_rescheduling,
)
from app.services.management_proposal import (
    get_pending_cancellation_proposal as get_pending_cancellation_proposal,
)
from app.services.management_proposal import (
    get_pending_rescheduling_proposal as get_pending_rescheduling_proposal,
)


@tool("prepare_cancellation_proposal_tool")
def prepare_cancellation_proposal_tool(
    appointment_id: str,
    patient_id: str,
    reason: Optional[str] = None,
    user_timezone: str = "UTC",
) -> str:
    """Prepares a cancellation proposal requiring HITL approval before final mutation."""
    try:
        a_uuid = uuid.UUID(appointment_id)
        p_uuid = uuid.UUID(patient_id)
        proposal = create_cancellation_proposal(
            appointment_id=a_uuid,
            patient_id=p_uuid,
            reason=reason,
            user_timezone=user_timezone,
        )
        return proposal.model_dump_json()
    except Exception as e:
        return f'{{"error": "Failed to prepare cancellation proposal: {str(e)}"}}'


@tool("prepare_rescheduling_proposal_tool")
def prepare_rescheduling_proposal_tool(
    appointment_id: str,
    patient_id: str,
    new_slot_id: str,
    reason: Optional[str] = None,
    user_timezone: str = "UTC",
) -> str:
    """Prepares a rescheduling proposal requiring HITL approval before final mutation."""
    try:
        a_uuid = uuid.UUID(appointment_id)
        p_uuid = uuid.UUID(patient_id)
        s_uuid = uuid.UUID(new_slot_id)
        proposal = create_rescheduling_proposal(
            appointment_id=a_uuid,
            patient_id=p_uuid,
            new_slot_id=s_uuid,
            reason=reason,
            user_timezone=user_timezone,
        )
        return proposal.model_dump_json()
    except Exception as e:
        return f'{{"error": "Failed to prepare rescheduling proposal: {str(e)}"}}'


@tool("list_user_appointments_tool")
def list_user_appointments_tool(
    patient_id: str,
) -> str:
    """Lists existing appointments for the authenticated patient."""
    try:
        p_uuid = uuid.UUID(patient_id)
        appt_service = AppointmentService()
        appts = appt_service.list_patient_appointments(p_uuid)
        import json

        data = [a.model_dump(mode="json") for a in appts]
        return json.dumps(data)
    except Exception as e:
        return f'{{"error": "Failed to list appointments: {str(e)}"}}'
