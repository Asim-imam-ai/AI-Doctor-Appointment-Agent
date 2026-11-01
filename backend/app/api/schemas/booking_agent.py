"""Schemas and models for Appointment Booking Agent with HITL."""

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.proposals.models import BookingProposal, BookingResult


class BookingApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class BookingApprovalRequest(BaseModel):
    booking_request_id: str = Field(
        ..., description="Unique booking request identifier"
    )
    proposal_version: int = Field(default=1, ge=1)
    decision: BookingApprovalDecision = Field(...)


class PrepareBookingApiRequest(BaseModel):
    model_config = {"extra": "forbid"}

    doctor_id: Optional[uuid.UUID] = Field(None, description="Doctor UUID if known")
    doctor_name: Optional[str] = Field(None, description="Doctor name")
    slot_id: Optional[uuid.UUID] = Field(
        None, description="Exact availability slot UUID if known"
    )
    message: str = Field(
        ..., min_length=1, max_length=1000, description="Booking request prompt"
    )
    user_timezone: str = Field("UTC", description="User preferred IANA timezone")
    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for appointment"
    )


class PrepareBookingApiResponse(BaseModel):
    request_id: str
    status: str
    message: str
    proposal: Optional[BookingProposal] = None
    requires_approval: bool = True
    error: Optional[str] = None


class ApproveBookingApiResponse(BaseModel):
    request_id: str
    status: str
    message: str
    booking_result: Optional[BookingResult] = None
    error: Optional[str] = None
