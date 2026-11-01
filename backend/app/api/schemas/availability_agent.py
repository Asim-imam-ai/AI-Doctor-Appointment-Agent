"""Schemas and models for Doctor Availability Agent."""

import uuid
from datetime import date as CalendarDate
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TimeOfDay(str, Enum):
    MORNING = "MORNING"
    AFTERNOON = "AFTERNOON"
    EVENING = "EVENING"


class AvailabilitySearchCriteria(BaseModel):
    model_config = ConfigDict(extra="ignore")

    doctor_id: Optional[uuid.UUID] = Field(None, description="Specific doctor UUID")
    doctor_name: Optional[str] = Field(None, description="Doctor name or partial name")
    specialty: Optional[str] = Field(
        None, description="Medical specialty (e.g., Cardiology, Dermatology)"
    )
    location: Optional[str] = Field(None, description="City or clinic location")
    date: Optional[str] = Field(None, description="Date in YYYY-MM-DD format")
    time_of_day: Optional[TimeOfDay] = Field(
        None, description="Controlled time window (MORNING, AFTERNOON, EVENING)"
    )
    user_timezone: str = Field(
        "UTC", description="User preferred IANA timezone name (e.g. Asia/Karachi, UTC)"
    )
    limit: int = Field(20, ge=1, le=50, description="Maximum number of slots to return")


class AvailableSlotDetail(BaseModel):
    id: uuid.UUID
    doctor_id: uuid.UUID
    doctor_name: str
    specialty: Optional[str] = None
    clinic_name: Optional[str] = None
    location: Optional[str] = None
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"
    status: str = "AVAILABLE"


class AvailabilitySearchResult(BaseModel):
    slots: List[AvailableSlotDetail] = Field(default_factory=list)
    total: int = 0
    criteria: AvailabilitySearchCriteria


class AvailabilitySearchApiRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language request to check doctor availability",
    )
    user_timezone: str = Field("UTC", description="User preferred timezone string")
    doctor_id: Optional[uuid.UUID] = Field(
        None, description="Exact doctor for a date-specific search"
    )
    appointment_date: Optional[CalendarDate] = Field(
        None, description="Exact date in the user's timezone"
    )


class AvailabilitySearchApiResponse(BaseModel):
    request_id: str = Field(..., description="Unique request tracking UUID")
    status: str = Field(
        ..., description="Status of availability request (success/error)"
    )
    message: str = Field(..., description="User-facing availability summary message")
    slots: List[AvailableSlotDetail] = Field(
        default_factory=list, description="Structured available slot records"
    )
    error: Optional[str] = None
