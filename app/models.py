"""Domain models for AI Doctor Appointment Agent."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"
    BLOCKED = "BLOCKED"


class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    EXPIRED = "EXPIRED"


class PatientModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    external_user_id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=3, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    timezone: str = Field(default="UTC", max_length=50)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


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


class DoctorAvailabilityModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    doctor_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: AvailabilityStatus = AvailabilityStatus.AVAILABLE
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AppointmentModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus = AppointmentStatus.PENDING
    reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ReminderType(str, Enum):
    TWENTY_FOUR_HOURS_BEFORE = "24_HOURS_BEFORE"
    TWO_HOURS_BEFORE = "2_HOURS_BEFORE"


class ReminderStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SENT = "SENT"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    IN_APP = "IN_APP"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENDING = "SENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class ReminderModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    appointment_id: uuid.UUID
    patient_id: uuid.UUID
    reminder_type: ReminderType
    scheduled_at: datetime
    status: ReminderStatus = ReminderStatus.PENDING
    timezone: str = "UTC"
    idempotency_key: str
    sent_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NotificationPreferenceModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    patient_id: uuid.UUID
    reminders_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    in_app_enabled: bool = True
    timezone: str = "UTC"
    created_at: datetime = Field(default_factory=datetime.now)


class NotificationDeliveryModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    reminder_id: uuid.UUID
    patient_id: uuid.UUID
    channel: NotificationChannel = NotificationChannel.EMAIL
    recipient: str
    subject: str
    body: str
    status: NotificationStatus = NotificationStatus.PENDING
    provider_response_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    DELETED = "DELETED"


class MemoryType(str, Enum):
    PREFERRED_SPECIALTY = "PREFERRED_SPECIALTY"
    PREFERRED_DOCTOR = "PREFERRED_DOCTOR"
    PREFERRED_TIME_RANGE = "PREFERRED_TIME_RANGE"
    TIMEZONE = "TIMEZONE"


class MemorySource(str, Enum):
    EXPLICIT_USER = "EXPLICIT_USER"
    SYSTEM_INFERRED = "SYSTEM_INFERRED"


class ConversationModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    patient_id: uuid.UUID
    title: str = Field(default="New Conversation", max_length=255)
    status: ConversationStatus = ConversationStatus.ACTIVE
    summary: Optional[str] = None
    last_message_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class ConversationMessageModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    conversation_id: uuid.UUID
    role: str = Field(..., max_length=50)  # user, assistant, system, tool
    content: str = Field(..., max_length=4000)
    metadata: Optional[dict] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


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
