"""Schemas and models for Appointment Cancellation & Rescheduling Agent with HITL (Phase 6)."""

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.proposals.models import (
    CancellationProposal,
    CancellationResult,
    ReschedulingProposal,
    ReschedulingResult,
)


class CancellationApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class CancellationApprovalRequest(BaseModel):
    cancellation_request_id: str = Field(
        ..., description="Unique cancellation request identifier"
    )
    proposal_version: int = Field(default=1, ge=1)
    decision: CancellationApprovalDecision = Field(...)


class ReschedulingApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ReschedulingApprovalRequest(BaseModel):
    reschedule_request_id: str = Field(
        ..., description="Unique reschedule request identifier"
    )
    proposal_version: int = Field(default=1, ge=1)
    decision: ReschedulingApprovalDecision = Field(...)


class PrepareCancellationApiRequest(BaseModel):
    model_config = {"extra": "forbid"}

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
    model_config = {"extra": "forbid"}

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
