"""Appointment schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    EXPIRED = "EXPIRED"


class AppointmentBase(BaseModel):
    doctor_id: str
    patient_id: str
    start_time: datetime
    end_time: datetime
    reason: Optional[str] = Field(None, max_length=255)


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentResponse(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: AppointmentStatus = AppointmentStatus.PENDING
    created_at: datetime

    @field_validator("id", "doctor_id", "patient_id", mode="before")
    @classmethod
    def serialize_uuid_ids(cls, value):
        return str(value) if isinstance(value, UUID) else value
