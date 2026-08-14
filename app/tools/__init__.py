"""Tools package exports and allowlist configuration."""

from app.tools.availability_search import search_available_slots_tool
from app.tools.booking_proposal import prepare_booking_proposal_tool
from app.tools.doctor_search import (
    get_doctor_details_tool,
    search_doctors_tool,
)
from app.tools.management_proposal import (
    list_user_appointments_tool,
    prepare_cancellation_proposal_tool,
    prepare_rescheduling_proposal_tool,
)

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
