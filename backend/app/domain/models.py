"""Shared model exports for stable cross-domain service and repository APIs."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.domain.appointments.models import AppointmentModel, AppointmentStatus
from app.domain.conversations.models import (
    ConversationMessageModel,
    ConversationModel,
    ConversationStatus,
)
from app.domain.doctors.models import DoctorModel, DoctorSpecialtyModel, SpecialtyModel
from app.domain.patients.models import PatientModel
from app.domain.scheduling.models import AvailabilityStatus, DoctorAvailabilityModel


class MemoryType(str, Enum):
    PREFERRED_SPECIALTY = "PREFERRED_SPECIALTY"
    PREFERRED_DOCTOR = "PREFERRED_DOCTOR"
    PREFERRED_TIME_RANGE = "PREFERRED_TIME_RANGE"
    TIMEZONE = "TIMEZONE"


class MemorySource(str, Enum):
    EXPLICIT_USER = "EXPLICIT_USER"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"


class MemoryItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    patient_id: uuid.UUID
    memory_type: MemoryType
    key: str = Field(..., min_length=1, max_length=100)
    value: str = Field(..., min_length=1, max_length=500)
    source: MemorySource = MemorySource.EXPLICIT_USER
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class KnowledgeCategory(str, Enum):
    APPOINTMENT_POLICY = "APPOINTMENT_POLICY"
    BOOKING_POLICY = "BOOKING_POLICY"
    CANCELLATION_POLICY = "CANCELLATION_POLICY"
    RESCHEDULING_POLICY = "RESCHEDULING_POLICY"
    CLINIC_INFORMATION = "CLINIC_INFORMATION"
    DEPARTMENT_INFORMATION = "DEPARTMENT_INFORMATION"
    SPECIALTY_INFORMATION = "SPECIALTY_INFORMATION"
    PREPARATION_INFORMATION = "PREPARATION_INFORMATION"
    FAQ = "FAQ"


class KnowledgeDocumentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    ARCHIVED = "ARCHIVED"


class KnowledgeDocumentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: str = Field(..., min_length=1, max_length=255)
    category: KnowledgeCategory
    version: str = Field(default="1.0", max_length=50)
    status: KnowledgeDocumentStatus = KnowledgeDocumentStatus.ACTIVE
    source: str = Field(..., max_length=255)
    content_hash: str = Field(..., max_length=64)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class KnowledgeChunkModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    document_id: uuid.UUID
    chunk_index: int = Field(..., ge=0)
    content: str = Field(..., min_length=1)
    embedding: Optional[list[float]] = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


__all__ = [
    "AppointmentModel",
    "AppointmentStatus",
    "AvailabilityStatus",
    "ConversationMessageModel",
    "ConversationModel",
    "ConversationStatus",
    "DoctorAvailabilityModel",
    "DoctorModel",
    "DoctorSpecialtyModel",
    "KnowledgeCategory",
    "KnowledgeChunkModel",
    "KnowledgeDocumentModel",
    "KnowledgeDocumentStatus",
    "MemoryItemModel",
    "MemorySource",
    "MemoryType",
    "PatientModel",
    "SpecialtyModel",
]
