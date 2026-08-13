"""Schemas and models for Appointment Booking Agent with HITL."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ProposalStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    SLOT_UNAVAILABLE = "SLOT_UNAVAILABLE"
    BOOKED = "BOOKED"
    FAILED = "FAILED"


class BookingProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    booking_request_id: str = Field(
        ..., description="Unique booking request UUID string"
    )
    proposal_version: int = Field(default=1, ge=1)
    patient_id: uuid.UUID
    patient_name: str
    doctor_id: uuid.UUID
    doctor_name: str
    slot_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    clinic_name: Optional[str] = None
    reason: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING_APPROVAL
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)


class BookingApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class BookingApprovalRequest(BaseModel):
    booking_request_id: str = Field(
        ..., description="Unique booking request identifier"
    )
    proposal_version: int = Field(default=1, ge=1)
    decision: BookingApprovalDecision = Field(...)
    patient_id: uuid.UUID = Field(..., description="Authenticated patient UUID")


class BookingResult(BaseModel):
    booking_request_id: str
    appointment_id: Optional[uuid.UUID] = None
    status: ProposalStatus
    doctor_name: str
    patient_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: str = "UTC"
    message: str


class PrepareBookingApiRequest(BaseModel):
    patient_id: uuid.UUID = Field(..., description="Authenticated patient UUID")
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
