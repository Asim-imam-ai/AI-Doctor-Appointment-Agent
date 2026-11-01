"""State passed between the intent router and one domain workflow."""

from typing import Any, TypedDict


class OrchestratorState(TypedDict, total=False):
    user_message: str
    patient_id: str
    intent: str
    response: str
    error: str
    result: dict[str, Any]
