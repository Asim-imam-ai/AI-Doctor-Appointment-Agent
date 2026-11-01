"""Doctor and specialty domain models."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DoctorModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., min_length=1, max_length=255)
    bio: Optional[str] = None
    clinic_name: Optional[str] = None
    location: Optional[str] = None
    consultation_duration: int = Field(default=30, ge=5, le=480)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class SpecialtyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class DoctorSpecialtyModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    doctor_id: uuid.UUID
    specialty_id: uuid.UUID
    created_at: datetime = Field(default_factory=datetime.now)
