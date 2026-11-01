"""Schemas and models for Doctor Discovery Tools."""

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DoctorSearchCriteria(BaseModel):
    model_config = ConfigDict(extra="ignore")

    specialty: Optional[str] = Field(
        None,
        description="Medical specialty to search for (e.g. Cardiology, Dermatology)",
    )
    doctor_name: Optional[str] = Field(
        None, description="Name or partial name of the doctor"
    )
    location: Optional[str] = Field(
        None, description="City, region, or location of doctor practice"
    )
    clinic_name: Optional[str] = Field(None, description="Clinic or hospital name")
    is_active: bool = Field(True, description="Whether to include only active doctors")
    limit: int = Field(
        10, ge=1, le=50, description="Maximum number of doctor records to return"
    )


class DoctorDetail(BaseModel):
    id: uuid.UUID
    name: str
    specialties: List[str] = Field(default_factory=list)
    clinic_name: Optional[str] = None
    location: Optional[str] = None
    bio: Optional[str] = None
    consultation_duration: int = 30
    is_active: bool = True


class DoctorSearchResult(BaseModel):
    doctors: List[DoctorDetail] = Field(default_factory=list)
    total: int = 0
    criteria: DoctorSearchCriteria


class DoctorSearchApiRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Natural language request or criteria to search doctors",
    )


class DoctorSearchApiResponse(BaseModel):
    request_id: str = Field(..., description="Unique request tracking UUID")
    status: str = Field(..., description="Status of search request (success/error)")
    message: str = Field(..., description="User-facing response message")
    doctors: List[DoctorDetail] = Field(
        default_factory=list, description="Structured doctor list returned by tool"
    )
    error: Optional[str] = None
