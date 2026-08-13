"""Tools package exports and allowlist configuration."""

from app.tools.availability_search import search_available_slots_tool
from app.tools.doctor_search import (
    get_doctor_details_tool,
    search_doctors_tool,
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

__all__ = [
    "search_doctors_tool",
    "get_doctor_details_tool",
    "search_available_slots_tool",
    "DOCTOR_DISCOVERY_TOOLS",
    "AVAILABILITY_TOOLS",
]
