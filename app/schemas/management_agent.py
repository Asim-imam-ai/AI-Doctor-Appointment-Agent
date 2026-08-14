"""Schemas and models for Appointment Cancellation & Rescheduling Agent with HITL (Phase 6)."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.booking_agent import ProposalStatus


class CancellationProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    cancellation_request_id: str = Field(
        ..., description="Unique cancellation request UUID string"
    )
    proposal_version: int = Field(default=1, ge=1)
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    doctor_id: uuid.UUID
    doctor_name: str
    appointment_start: datetime
    appointment_end: datetime
    timezone: str = "UTC"
    reason: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING_APPROVAL
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)


class ReschedulingProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reschedule_request_id: str = Field(
        ..., description="Unique reschedule request UUID string"
    )
    proposal_version: int = Field(default=1, ge=1)
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    patient_name: str
    doctor_id: uuid.UUID
    doctor_name: str
    old_start_time: datetime
    old_end_time: datetime
    new_slot_id: uuid.UUID
    new_start_time: datetime
    new_end_time: datetime
    timezone: str = "UTC"
    reason: Optional[str] = None
    status: ProposalStatus = ProposalStatus.PENDING_APPROVAL
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.now)


class CancellationApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class CancellationApprovalRequest(BaseModel):
    cancellation_request_id: str = Field(
        ..., description="Unique cancellation request identifier"
    )
    proposal_version: int = Field(default=1, ge=1)
    decision: CancellationApprovalDecision = Field(...)
    patient_id: uuid.UUID = Field(..., description="Authenticated patient UUID")


class ReschedulingApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ReschedulingApprovalRequest(BaseModel):
    reschedule_request_id: str = Field(
        ..., description="Unique reschedule request identifier"
    )
    proposal_version: int = Field(default=1, ge=1)
    decision: ReschedulingApprovalDecision = Field(...)
    patient_id: uuid.UUID = Field(..., description="Authenticated patient UUID")


class CancellationResult(BaseModel):
    cancellation_request_id: str
    appointment_id: Optional[uuid.UUID] = None
    status: ProposalStatus
    doctor_name: str
    patient_name: str
    message: str


class ReschedulingResult(BaseModel):
    reschedule_request_id: str
    appointment_id: Optional[uuid.UUID] = None
    status: ProposalStatus
    doctor_name: str
    patient_name: str
    new_start_time: Optional[datetime] = None
    new_end_time: Optional[datetime] = None
    timezone: str = "UTC"
    message: str


class PrepareCancellationApiRequest(BaseModel):
    patient_id: uuid.UUID = Field(..., description="Authenticated patient UUID")
    appointment_id: Optional[uuid.UUID] = Field(
        None, description="Appointment UUID to cancel if known"
    )
    message: str = Field(
        ..., min_length=1, max_length=1000, description="Cancellation prompt"
    )
    user_timezone: str = Field("UTC", description="User preferred IANA timezone")
    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for cancellation"
    )


class PrepareCancellationApiResponse(BaseModel):
    request_id: str
    status: str
    message: str
    proposal: Optional[CancellationProposal] = None
    requires_approval: bool = True
    error: Optional[str] = None


class ApproveCancellationApiResponse(BaseModel):
    request_id: str
    status: str
    message: str
    cancellation_result: Optional[CancellationResult] = None
    error: Optional[str] = None


class PrepareReschedulingApiRequest(BaseModel):
    patient_id: uuid.UUID = Field(..., description="Authenticated patient UUID")
    appointment_id: Optional[uuid.UUID] = Field(
        None, description="Appointment UUID to reschedule if known"
    )
    new_slot_id: Optional[uuid.UUID] = Field(
        None, description="Replacement slot UUID if selected"
    )
    message: str = Field(
        ..., min_length=1, max_length=1000, description="Rescheduling prompt"
    )
    user_timezone: str = Field("UTC", description="User preferred IANA timezone")
    reason: Optional[str] = Field(
        None, max_length=500, description="Reason for rescheduling"
    )


class PrepareReschedulingApiResponse(BaseModel):
    request_id: str
    status: str
    message: str
    proposal: Optional[ReschedulingProposal] = None
    requires_approval: bool = True
    error: Optional[str] = None


class ApproveReschedulingApiResponse(BaseModel):
    request_id: str
    status: str
    message: str
    rescheduling_result: Optional[ReschedulingResult] = None
    error: Optional[str] = None
