"""Tools package exports and allowlist configuration."""

from app.tools.doctor_search import (
    get_doctor_details_tool,
    search_doctors_tool,
)

# Read-Only Doctor Discovery Tool Allowlist
DOCTOR_DISCOVERY_TOOLS = [
    search_doctors_tool,
    get_doctor_details_tool,
]

__all__ = [
    "search_doctors_tool",
    "get_doctor_details_tool",
    "DOCTOR_DISCOVERY_TOOLS",
]
