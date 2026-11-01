"""Shared tool registry, allowlist enforcement, and execution helpers."""

import json
import logging
from typing import Any

from app.agentic.workflows.availability.tools import search_available_slots_tool
from app.agentic.workflows.booking.tools import prepare_booking_proposal_tool
from app.agentic.workflows.cancellation.tools import (
    list_user_appointments_tool,
    prepare_cancellation_proposal_tool,
    prepare_rescheduling_proposal_tool,
)
from app.agentic.workflows.doctor_discovery.tools import (
    get_doctor_details_tool,
    search_doctors_tool,
)

logger = logging.getLogger(__name__)


def execute_allowed_tool(
    tool_call: dict[str, Any],
    allowed_tools: list[Any],
    *,
    patient_id: str | None = None,
) -> str:
    """Execute one explicitly allowlisted LangChain tool with bounded error output."""
    name = tool_call.get("name")
    tool = next(
        (candidate for candidate in allowed_tools if candidate.name == name), None
    )
    if tool is None:
        return json.dumps({"error": "Tool is not allowed for this workflow."})
    try:
        arguments = dict(tool_call.get("args", {}))
        if patient_id is not None and "patient_id" in getattr(tool, "args", {}):
            arguments["patient_id"] = patient_id
        result = tool.invoke(arguments)
    except Exception:
        logger.exception("Allowlisted tool execution failed: %s", name)
        return json.dumps({"error": "Tool execution failed."})
    return result if isinstance(result, str) else json.dumps(result, default=str)


# Read-Only Doctor Discovery Tool Allowlist (Phase 3)
DOCTOR_DISCOVERY_TOOLS = [
    search_doctors_tool,
    get_doctor_details_tool,
]

# Read-Only Availability Agent Tool Allowlist (Phase 4)
AVAILABILITY_TOOLS = [
    search_available_slots_tool,
    search_doctors_tool,
    get_doctor_details_tool,
]

# Pre-Approval Booking Preparation Tool Allowlist (Phase 5)
BOOKING_PREPARE_TOOLS = [
    prepare_booking_proposal_tool,
    search_available_slots_tool,
    search_doctors_tool,
    get_doctor_details_tool,
]

# Pre-Approval Cancellation Tool Allowlist (Phase 6)
CANCELLATION_PREPARE_TOOLS = [
    prepare_cancellation_proposal_tool,
    list_user_appointments_tool,
]

# Pre-Approval Rescheduling Tool Allowlist (Phase 6)
RESCHEDULING_PREPARE_TOOLS = [
    prepare_rescheduling_proposal_tool,
    list_user_appointments_tool,
    search_available_slots_tool,
]

__all__ = [
    "search_doctors_tool",
    "get_doctor_details_tool",
    "search_available_slots_tool",
    "prepare_booking_proposal_tool",
    "prepare_cancellation_proposal_tool",
    "prepare_rescheduling_proposal_tool",
    "list_user_appointments_tool",
    "DOCTOR_DISCOVERY_TOOLS",
    "AVAILABILITY_TOOLS",
    "BOOKING_PREPARE_TOOLS",
    "CANCELLATION_PREPARE_TOOLS",
    "RESCHEDULING_PREPARE_TOOLS",
]
