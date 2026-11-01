"""Doctor discovery graph state."""

from typing import Optional

from app.agentic.common.state import CommonAgentState
from app.api.schemas.doctor_discovery import DoctorSearchCriteria, DoctorSearchResult


class DoctorDiscoveryState(CommonAgentState, total=False):
    search_criteria: Optional[DoctorSearchCriteria]
    tool_results: Optional[DoctorSearchResult]
