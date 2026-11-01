"""Availability and scheduling domain models."""

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    BLOCKED = "BLOCKED"


class DoctorAvailabilityModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    doctor_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
