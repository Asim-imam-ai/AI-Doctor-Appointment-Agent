"""Chat message schemas."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.proposals.models import (
    BookingProposal,
    CancellationProposal,
    ReschedulingProposal,
)


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ChatMessage(BaseModel):
    role: MessageRole
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    message: str
    requires_hitl: bool = False
    action_type: Optional[str] = None
    booking_proposal: Optional[BookingProposal] = None
    cancellation_proposal: Optional[CancellationProposal] = None
    rescheduling_proposal: Optional[ReschedulingProposal] = None
