"""Agent schemas."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentStateSchema(BaseModel):
    session_id: str
    messages: list[Dict[str, Any]] = []
    current_intent: Optional[str] = None
    hitl_approved: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
