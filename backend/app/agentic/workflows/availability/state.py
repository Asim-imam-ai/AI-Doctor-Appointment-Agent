"""Availability graph state."""

from typing import Optional

from app.agentic.common.state import CommonAgentState
from app.api.schemas.availability_agent import (
    AvailabilitySearchCriteria,
    AvailabilitySearchResult,
)


class DoctorAvailabilityState(CommonAgentState, total=False):
    user_timezone: str
    availability_criteria: Optional[AvailabilitySearchCriteria]
    tool_results: Optional[AvailabilitySearchResult]
