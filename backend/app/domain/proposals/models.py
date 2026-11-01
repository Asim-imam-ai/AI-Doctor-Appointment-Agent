"""Domain models for the persisted human approval lifecycle."""

import uuid
from datetime import datetime, timezone
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
    booking_request_id: str
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CancellationProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cancellation_request_id: str
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ReschedulingProposal(BaseModel):
    model_config = ConfigDict(extra="ignore")
    reschedule_request_id: str
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


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
